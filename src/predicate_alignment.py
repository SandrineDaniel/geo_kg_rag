"""
predicate_alignment.py
======================
Aligns local KG predicates to standard ontology URIs (DBpedia Ontology, Schema.org).
 
Strategy:
  1. PRIMARY - Manual mapping: each local predicate is mapped to a well-known
     standard URI based on domain knowledge. This guarantees at least one
     alignment per predicate, regardless of DBpedia coverage.
  2. FALLBACK - DBpedia SPARQL: for predicates not in the manual map, we query
     DBpedia to find predicates that co-occur between linked entity pairs.
     Only candidates with enough hits (>= threshold_hits) are kept.
 
Why manual mapping is necessary:
  Our predicates (oppose, deploy, attack...) are domain-specific geopolitical
  relations extracted from news articles. DBpedia is encyclopedic and rarely
  contains direct triples between two entities with these exact verbs.
  As a result, the DBpedia fallback alone produces 0 alignments (tested).
  The manual map bridges this gap by grounding relations in standard vocabularies.
"""
 
import os
import csv
import time
from collections import Counter, defaultdict
 
import requests
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL
 
from src.namespaces import EX
 
# ── DBpedia SPARQL endpoint ──────────────────────────────────────────────────
DBP_ENDPOINT = "http://dbpedia.org/sparql"
USER_AGENT = {"User-Agent": "KB-Lab/1.0"}
 
# ── Predicates to skip (metadata / structural triples) ───────────────────────
IGNORE_PREDICATES = {
    str(RDF.type),
    str(RDFS.label),
    str(OWL.sameAs),
    str(EX.sourceUrl),
}
 
# ── Manual alignment table ───────────────────────────────────────────────────
# Maps each local predicate name to a list of candidate standard URIs.
# Multiple candidates are listed in decreasing preference order;
# the first one will be used as the primary owl:equivalentProperty alignment.
# Sources: DBpedia Ontology (dbo:), Schema.org (schema:), SKOS (skos:)
MANUAL_ALIGNMENT = {
    "oppose": [
        "http://dbpedia.org/ontology/opponent",          # direct semantic match
        "http://www.w3.org/2004/02/skos/core#related",   # broader fallback
    ],
    "support": [
        "http://dbpedia.org/ontology/related",
        "http://schema.org/knows",
    ],
    "deploy": [
        "http://dbpedia.org/ontology/militaryBranch",    # closest in DBO
        "http://dbpedia.org/ontology/militaryUnit",
    ],
    "meet": [
        "http://schema.org/knows",                       # diplomatic/social meeting
        "http://dbpedia.org/ontology/related",
    ],
    "attack": [
        "http://dbpedia.org/ontology/isPartOfMilitaryConflict",
        "http://dbpedia.org/ontology/opponent",
    ],
    "located_in": [
        "http://dbpedia.org/ontology/location",          # standard geographic relation
        "http://schema.org/containedInPlace",
    ],
    "announce": [
        "http://dbpedia.org/ontology/related",
        "http://schema.org/mentions",
    ],
    "claim": [
        "http://dbpedia.org/ontology/related",
        "http://www.w3.org/2004/02/skos/core#related",
    ],
    "defend": [
        "http://dbpedia.org/ontology/militaryBranch",
        "http://dbpedia.org/ontology/related",
    ],
    "intervene_in": [
        "http://dbpedia.org/ontology/isPartOfMilitaryConflict",
        "http://dbpedia.org/ontology/related",
    ],
    "operate": [
        "http://dbpedia.org/ontology/operator",
        "http://dbpedia.org/ontology/related",
    ],
    "related_to": [
        "http://www.w3.org/2004/02/skos/core#related",
        "http://dbpedia.org/ontology/related",
    ],
}
 
 
def canonicalize_dbpedia_uri(uri: str) -> str:
    """Normalize DBpedia URIs to http:// (some APIs return https://)."""
    if uri.startswith("https://dbpedia.org/"):
        return "http://dbpedia.org/" + uri[len("https://dbpedia.org/"):]
    return uri
 
 
def dbpedia_predicates_between(s_ext: str, o_ext: str, limit: int = 50,
                               endpoint: str = DBP_ENDPOINT):
    """
    Query DBpedia SPARQL to find predicates that exist between two linked entities.
    Returns a list of (predicate_uri, predicate_label) tuples.
    Used as a fallback when no manual mapping exists for a predicate.
    """
    s_ext = canonicalize_dbpedia_uri(s_ext)
    o_ext = canonicalize_dbpedia_uri(o_ext)
 
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?p ?pLabel WHERE {{
      <{s_ext}> ?p <{o_ext}> .
      OPTIONAL {{
        ?p rdfs:label ?pLabel .
        FILTER(lang(?pLabel) = "en")
      }}
    }} LIMIT {limit}
    """
    params = {"query": query, "format": "application/sparql-results+json"}
    try:
        r = requests.get(endpoint, params=params, timeout=30, headers=USER_AGENT)
    except requests.RequestException:
        return []
 
    if r.status_code != 200:
        return []
 
    data = r.json()
    return [
        (b["p"]["value"], b.get("pLabel", {}).get("value", ""))
        for b in data.get("results", {}).get("bindings", [])
    ]
 
 
def collect_private_relation_triples(g: Graph, rel_prefixes=None):
    """
    Collect all (s, p, o) triples whose predicate belongs to our local KG namespace.
    Structural predicates (rdf:type, rdfs:label, owl:sameAs, ex:sourceUrl) are excluded.
    """
    if rel_prefixes is None:
        rel_prefixes = [str(EX), str(EX) + "rel/"]
 
    return [
        (s, p, o) for s, p, o in g
        if isinstance(s, URIRef) and isinstance(p, URIRef) and isinstance(o, URIRef)
        and str(p) not in IGNORE_PREDICATES
        and any(str(p).startswith(pref) for pref in rel_prefixes)
    ]
 
 
def build_sameas_index(g: Graph):
    """
    Build an index: local_uri -> list of external (DBpedia) URIs
    based on owl:sameAs triples in the graph.
    """
    sameas = defaultdict(list)
    for s, _, o in g.triples((None, OWL.sameAs, None)):
        if isinstance(s, URIRef):
            sameas[s].append(str(o))
    return sameas
 
 
def predicate_local_name(p: URIRef) -> str:
    """Extract a human-readable name from a local predicate URI."""
    ps = str(p).rstrip("/")
    return ps.split("/")[-1]
 
 
def run_predicate_alignment(
    input_ttl: str,
    out_csv: str,
    out_ttl: str,
    top_predicates: int = 30,
    examples_per_predicate: int = 5,
    dbpedia_limit: int = 50,
    threshold_hits: int = 2,      # lowered from 3 to allow more DBpedia matches
    sleep_seconds: float = 0.2,
):
    """
    Main function: aligns local KG predicates to standard ontology URIs.
 
    Steps:
      1. Load the aligned KG (step 2 output).
      2. Identify the most frequent local relation predicates.
      3. For each predicate:
         a. Apply manual mapping if available (PRIMARY strategy).
         b. Otherwise query DBpedia SPARQL using entity pairs (FALLBACK strategy).
      4. Write alignment triples as owl:equivalentProperty to a Turtle file.
      5. Write a CSV summary of all candidates for inspection.
    """
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    os.makedirs(os.path.dirname(out_ttl), exist_ok=True)
 
    # Load graph
    g = Graph()
    g.parse(input_ttl, format="turtle")
 
    # Collect relation triples and rank predicates by frequency
    rel_triples = collect_private_relation_triples(g)
    print(f"Relation triples found: {len(rel_triples)}")
 
    pred_counts = Counter(str(p) for _, p, _ in rel_triples)
    top_preds = [URIRef(p) for p, _ in pred_counts.most_common(top_predicates)]
 
    sameas = build_sameas_index(g)
 
    rows = []          # rows for the CSV report
    proposed = Graph() # graph that will hold owl:equivalentProperty triples
    proposed.bind("owl", OWL)
    proposed.bind("rdfs", RDFS)
 
    alignments_made = 0
    cache = {}  # cache (s_ext, o_ext) -> DBpedia predicates to avoid redundant queries
 
    for p in top_preds:
        local_name = predicate_local_name(p)
 
        # ── PRIMARY: manual mapping ──────────────────────────────────────────
        if local_name in MANUAL_ALIGNMENT:
            candidates = MANUAL_ALIGNMENT[local_name]
 
            # The first candidate is the primary alignment
            primary_uri = candidates[0]
            proposed.add((p, OWL.equivalentProperty, URIRef(primary_uri)))
            alignments_made += 1
 
            # Log all candidates in the CSV for transparency
            for rank, cand_uri in enumerate(candidates):
                rows.append([
                    local_name,
                    str(p),
                    cand_uri,
                    "manual mapping" if rank == 0 else "manual alternative",
                    "MANUAL",
                    "-",
                ])
 
            print(f"[MANUAL]   {local_name} → {primary_uri}")
            continue
 
        # ── FALLBACK: DBpedia SPARQL ─────────────────────────────────────────
        # Collect entity pairs where both endpoints have a sameAs link
        examples = []
        for s, pp, o in rel_triples:
            if pp != p:
                continue
            if sameas.get(s) and sameas.get(o):
                s_ext = canonicalize_dbpedia_uri(sameas[s][0])
                o_ext = canonicalize_dbpedia_uri(sameas[o][0])
                examples.append((s, o, s_ext, o_ext))
            if len(examples) >= examples_per_predicate:
                break
 
        if not examples:
            print(f"[SKIP]     {local_name} — no linked entity pairs found")
            continue
 
        candidate_counter = Counter()
        candidate_labels = {}
 
        for (_, _, s_ext, o_ext) in examples:
            key = (s_ext, o_ext)
            if key not in cache:
                cache[key] = dbpedia_predicates_between(s_ext, o_ext, limit=dbpedia_limit)
                time.sleep(sleep_seconds)
            for pred_uri, pred_label in cache[key]:
                candidate_counter[pred_uri] += 1
                candidate_labels.setdefault(pred_uri, pred_label)
 
        # Log all DBpedia candidates in the CSV
        for cand_uri, hits in candidate_counter.most_common(10):
            rows.append([
                local_name, str(p), cand_uri,
                candidate_labels.get(cand_uri, ""),
                hits, len(examples),
            ])
 
        # Only align if the best candidate has enough supporting examples
        if candidate_counter:
            best_uri, best_hits = candidate_counter.most_common(1)[0]
            if best_hits >= threshold_hits:
                proposed.add((p, OWL.equivalentProperty, URIRef(best_uri)))
                alignments_made += 1
                print(f"[DBPEDIA]  {local_name} → {best_uri} (hits={best_hits})")
            else:
                print(f"[NO MATCH] {local_name} — best hits={best_hits} < threshold={threshold_hits}")
 
    # ── Save outputs ─────────────────────────────────────────────────────────
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "private_pred_label", "private_pred_uri",
            "candidate_uri", "candidate_label", "hits", "num_examples"
        ])
        w.writerows(rows)
 
    proposed.serialize(out_ttl, format="turtle")
 
    print(f"\nSaved candidates CSV : {out_csv}")
    print(f"Saved alignment TTL  : {out_ttl}")
    print(f"Total alignments made: {alignments_made}")