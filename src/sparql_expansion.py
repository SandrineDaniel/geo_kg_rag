"""
sparql_expansion.py
===================
Expands the local Knowledge Graph by fetching 1-hop Wikidata triples
for every entity linked via owl:sameAs during entity linking.

Why Wikidata instead of DBpedia?
---------------------------------
DBpedia expansion introduced ~97% wikiPageWikiLink triples — structural
hyperlinks with no semantic value. Wikidata uses direct properties (wdt:)
that are purely semantic: birthPlace, party, country, memberOf, etc.
This produces a smaller but much richer KB suitable for both KGE and RAG.

What is SPARQL?
---------------
SPARQL is the standard query language for RDF graphs (like SQL for databases).
We use it to fetch all (predicate, object) pairs for a given Wikidata entity.

Used by:
  - scripts/run_sparql_expansion.py

Functions:
  - query_wikidata()           : sends a SPARQL query to Wikidata endpoint
  - expand_one_hop()           : fetches 1-hop triples for one entity
  - collect_aligned_entities() : finds all Wikidata URIs via owl:sameAs
  - run_sparql_expansion()     : main expansion function
"""

import time
import requests
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import OWL, RDFS

# ── Wikidata SPARQL endpoint ──────────────────────────────────────────────────
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

HEADERS = {
    "User-Agent": "GeoKGRAG/1.0 (sandrine.daniel@edu.devinci.fr; student project)",
    "Accept": "application/sparql-results+json",
}

# ── Namespaces ────────────────────────────────────────────────────────────────
WDT = Namespace("http://www.wikidata.org/prop/direct/")
WD  = Namespace("http://www.wikidata.org/entity/")


def query_wikidata(query: str) -> dict:
    """
    Send a SPARQL SELECT query to the Wikidata public endpoint.
    Returns the parsed JSON response.
    """
    r = requests.get(
        WIKIDATA_ENDPOINT,
        params={"query": query, "format": "application/sparql-results+json"},
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def expand_one_hop(qid: str, per_entity_limit: int) -> list:
    """
    Fetch Wikidata properties using the Wikidata API (wbgetentities)
    instead of SPARQL — much more reliable and less rate-limited.
    """
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "format": "json",
        "props": "claims",
        "languages": "en",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        data = r.json()
        entity = data.get("entities", {}).get(qid, {})
        claims = entity.get("claims", {})

        results = []
        count = 0
        for prop_id, claim_list in claims.items():
            if count >= per_entity_limit:
                break
            for claim in claim_list:
                if count >= per_entity_limit:
                    break
                mainsnak = claim.get("mainsnak", {})
                if mainsnak.get("snaktype") != "value":
                    continue
                datavalue = mainsnak.get("datavalue", {})
                val_type  = datavalue.get("type")
                value     = datavalue.get("value")

                if val_type == "wikibase-entityid":
                    obj_qid = value.get("id")
                    if obj_qid:
                        results.append({
                            "p": {"value": f"http://www.wikidata.org/prop/direct/{prop_id}"},
                            "o": {"type": "uri", "value": f"http://www.wikidata.org/entity/{obj_qid}"}
                        })
                        count += 1
                elif val_type == "string":
                    results.append({
                        "p": {"value": f"http://www.wikidata.org/prop/direct/{prop_id}"},
                        "o": {"type": "literal", "value": str(value)}
                    })
                    count += 1
                elif val_type == "time":
                    results.append({
                        "p": {"value": f"http://www.wikidata.org/prop/direct/{prop_id}"},
                        "o": {"type": "literal", "value": value.get("time", "")}
                    })
                    count += 1

        return results

    except Exception as e:
        print(f"  API error for {qid}: {e}")
        return []


def collect_aligned_entities(g: Graph) -> dict:
    """
    Extract all Wikidata QIDs linked from our local KG via owl:sameAs.
    Returns a dict: local_uri -> wikidata_qid (e.g. "Q22686")
    """
    aligned = {}
    for s, _, o in g.triples((None, OWL.sameAs, None)):
        uri = str(o)
        if "wikidata.org/entity/Q" in uri:
            qid = uri.split("/")[-1]
            aligned[str(s)] = qid
    return aligned


def run_sparql_expansion(
    input_ttl:        str,
    output_ttl:       str,
    max_triples:      int   = 200_000,
    per_entity_limit: int   = 200,
    sleep_seconds:    float = 1.0,   # Wikidata rate limit: be polite!
) -> dict:
    """
    Main expansion function.

    For each Wikidata entity linked in the KG (via owl:sameAs):
      1. Query Wikidata for its 1-hop direct properties (wdt:).
      2. Add the returned triples to the local graph.
      3. Stop early if the graph reaches max_triples.

    Returns a stats dict for the final report.
    """
    # Load the aligned KG (output of entity linking step)
    g = Graph()
    g.parse(input_ttl, format="turtle")
    initial_triples = len(g)
    print(f"Loaded graph: {initial_triples} triples")

    # Collect Wikidata QIDs from owl:sameAs links
    aligned = collect_aligned_entities(g)
    print(f"Aligned Wikidata entities to expand: {len(aligned)}")

    expanded_count = 0
    failed_count   = 0
    added_total    = 0
    seen_qids = set()
    unique_aligned = {}
    for local_uri, qid in aligned.items():
        if qid not in seen_qids:
           seen_qids.add(qid)
           unique_aligned[local_uri] = qid

    print(f"Unique QIDs to expand: {len(unique_aligned)} (was {len(aligned)})")

    for local_uri, qid in unique_aligned.items():
        if len(g) >= max_triples:
            print(f"Reached max_triples cap ({max_triples}), stopping.")
            break

        results = expand_one_hop(qid, per_entity_limit)
        if not results:
            failed_count += 1
            continue

        added_here = 0
        wd_uri = URIRef(f"http://www.wikidata.org/entity/{qid}")

        for row in results:
            p_str = row["p"]["value"]
            o_val = row["o"]

            p = URIRef(p_str)

            # Handle URI vs literal objects
            if o_val["type"] == "uri":
                o = URIRef(o_val["value"])
            else:
                o = Literal(o_val["value"])

            # Add triple with the Wikidata URI as subject
            g.add((wd_uri, p, o))
            # Also link from local URI for connectivity
            g.add((URIRef(local_uri), p, o))
            added_here += 2

            if len(g) >= max_triples:
                break

        added_total    += added_here
        expanded_count += 1
        short_name = local_uri.split("/")[-1]
        print(f"  ✓ {short_name} ({qid}) → +{added_here//2} triples (total: {len(g)})")
        time.sleep(sleep_seconds)

    # Serialize the expanded graph
    import os
    os.makedirs(os.path.dirname(output_ttl), exist_ok=True)
    g.serialize(output_ttl, format="turtle")

    stats = {
        "initial_triples":    initial_triples,
        "final_triples":      len(g),
        "added_triples":      added_total,
        "entities_expanded":  expanded_count,
        "entities_failed":    failed_count,
        "entities_total":     len(aligned),
    }

    print(f"\nExpansion complete.")
    print(f"  Triples before : {initial_triples:,}")
    print(f"  Triples added  : {added_total:,}")
    print(f"  Triples after  : {len(g):,}")
    print(f"  Saved to       : {output_ttl}")

    return stats