"""
entity_linking.py
=================
Entity linking module: connects local KG entities to Wikidata resources.

For each entity label in the KG, queries the Wikidata Search API to find
a matching Wikidata item (QID). If a confident match is found, an owl:sameAs
triple is added linking the local entity to its Wikidata URI.

Entities that cannot be linked are classified as local subclasses
(LocalPerson, LocalOrganization, LocalPlace) defined in the local ontology.

Confidence score:
  1.0 if the label exactly matches the Wikidata item label
  0.7 if it matches an alias
  0.5 if it is a partial match
  Threshold: 0.5

Used by:
  - scripts/run_entity_linking.py

Functions:
  - wikidata_lookup()      : queries Wikidata Search API for a label
  - add_local_classes()    : adds LocalPerson/Org/Place classes to the graph
  - save_local_ontology()  : serializes the local ontology to Turtle
  - run_entity_linking()   : main linking function
"""

import os
import csv
import time
from collections import Counter
from rdflib import Graph, URIRef, Literal, Namespace
import requests
from rdflib.namespace import RDF, RDFS, OWL

from src.namespaces import EX, SCHEMA

# ── Wikidata Search API ───────────────────────────────────────────────────────
WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": "KB-Lab-EntityLinking/1.0 (student project)",
    "Accept": "application/json",
}


def wikidata_lookup(label: str, language: str = "en", max_hits: int = 5):
    for attempt in range(3):  # 3 tentatives
        try:
            response = requests.get(
                WIKIDATA_SEARCH_URL,
                params={
                    "action": "wbsearchentities",
                    "search": label,
                    "language": language,
                    "format": "json",
                    "limit": max_hits,
                },
                headers=HEADERS,
                timeout=20,
            )
            if response.status_code == 200 and response.text.strip():
                data = response.json()
                results = data.get("search", [])
                if results:
                    best = results[0]
                    qid = best.get("id", "")
                    if not qid:
                        return None, 0.0
                    uri = f"http://www.wikidata.org/entity/{qid}"
                    result_label = best.get("label", "").lower()
                    query_lower = label.lower()
                    if result_label == query_lower:
                        conf = 1.0
                    elif result_label.startswith(query_lower):
                        conf = 0.5
                    else:
                        conf = 0.4
                    return uri, conf
                return None, 0.0
        except Exception:
            pass
        time.sleep(2 * (attempt + 1))  # 2s, 4s, 6s entre retries
    return None, 0.0


def add_local_classes(g: Graph):
    """Add LocalPerson, LocalOrganization, LocalPlace classes to the graph."""
    g.add((EX.LocalPerson,       RDF.type,        RDFS.Class))
    g.add((EX.LocalPerson,       RDFS.subClassOf, SCHEMA.Person))
    g.add((EX.LocalOrganization, RDF.type,        RDFS.Class))
    g.add((EX.LocalOrganization, RDFS.subClassOf, SCHEMA.Organization))
    g.add((EX.LocalPlace,        RDF.type,        RDFS.Class))
    g.add((EX.LocalPlace,        RDFS.subClassOf, SCHEMA.Place))


def save_local_ontology(output_path: str):
    """Serialize the local ontology (LocalPerson/Org/Place) to Turtle."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    onto = Graph()
    onto.bind("ex",     EX)
    onto.bind("schema", SCHEMA)
    onto.bind("rdfs",   RDFS)

    for triple in [
        (EX.LocalPerson,       RDF.type,        RDFS.Class),
        (EX.LocalPerson,       RDFS.subClassOf, SCHEMA.Person),
        (EX.LocalOrganization, RDF.type,        RDFS.Class),
        (EX.LocalOrganization, RDFS.subClassOf, SCHEMA.Organization),
        (EX.LocalPlace,        RDF.type,        RDFS.Class),
        (EX.LocalPlace,        RDFS.subClassOf, SCHEMA.Place),
    ]:
        onto.add(triple)

    onto.serialize(output_path, format="turtle")


# Manually add important geopolitical entities missing from NER
def add_core_entities(ttl_path: str):
    g = Graph()
    g.parse(ttl_path, format="turtle")
    g.bind("ex", EX)
    g.bind("schema", SCHEMA)

    core_entities = [
        # (local_uri, label, type, wikidata_uri)
        (EX["person/donald_trump"],     "Donald Trump",        SCHEMA.Person,       "http://www.wikidata.org/entity/Q22686"),
        (EX["person/mette_frederiksen"],"Mette Frederiksen",   SCHEMA.Person,       "http://www.wikidata.org/entity/Q27390858"),
        (EX["person/mark_rutte"],       "Mark Rutte",          SCHEMA.Person,       "http://www.wikidata.org/entity/Q57792"),
        (EX["person/ursula_leyen"],     "Ursula von der Leyen",SCHEMA.Person,       "http://www.wikidata.org/entity/Q20522949"),
        (EX["person/putin"],            "Vladimir Putin",      SCHEMA.Person,       "http://www.wikidata.org/entity/Q7747"),
        (EX["person/zelenskyy"],        "Volodymyr Zelenskyy", SCHEMA.Person,       "http://www.wikidata.org/entity/Q2790390"),
        (EX["person/macron"],           "Emmanuel Macron",     SCHEMA.Person,       "http://www.wikidata.org/entity/Q3052772"),
        (EX["place/greenland"],         "Greenland",           SCHEMA.Place,        "http://www.wikidata.org/entity/Q223"),
        (EX["place/denmark"],           "Denmark",             SCHEMA.Place,        "http://www.wikidata.org/entity/Q35"),
        (EX["place/russia"],            "Russia",              SCHEMA.Place,        "http://www.wikidata.org/entity/Q159"),
        (EX["place/france"],            "France",              SCHEMA.Place,        "http://www.wikidata.org/entity/Q142"),
        (EX["place/germany"],           "Germany",             SCHEMA.Place,        "http://www.wikidata.org/entity/Q183"),
        (EX["place/united_states"],     "United States",       SCHEMA.Place,        "http://www.wikidata.org/entity/Q30"),
        (EX["place/arctic"],            "Arctic",              SCHEMA.Place,        "http://www.wikidata.org/entity/Q22"),
        (EX["place/ukraine"],           "Ukraine",             SCHEMA.Place,        "http://www.wikidata.org/entity/Q212"),
        (EX["place/norway"],            "Norway",              SCHEMA.Place,        "http://www.wikidata.org/entity/Q20"),
        (EX["place/sweden"],            "Sweden",              SCHEMA.Place,        "http://www.wikidata.org/entity/Q34"),
        (EX["place/iceland"],           "Iceland",             SCHEMA.Place,        "http://www.wikidata.org/entity/Q189"),
        (EX["org/nato"],                "NATO",                SCHEMA.Organization, "http://www.wikidata.org/entity/Q7184"),
        (EX["org/european_union"],      "European Union",      SCHEMA.Organization, "http://www.wikidata.org/entity/Q458"),
        (EX["org/arctic_council"],      "Arctic Council",      SCHEMA.Organization, "http://www.wikidata.org/entity/Q145165"),
        (EX["org/un"],                  "United Nations",      SCHEMA.Organization, "http://www.wikidata.org/entity/Q1065"),
    ]

    for uri, label, rdf_type, wd_uri in core_entities:
        g.add((uri, RDF.type, rdf_type))
        g.add((uri, RDFS.label, Literal(label)))
        g.add((uri, OWL.sameAs, URIRef(wd_uri)))

    g.serialize(ttl_path, format="turtle")
    print(f"Added {len(core_entities)} core entities to {ttl_path}")



def run_entity_linking(
    input_ttl:    str,
    output_ttl:   str,
    mapping_csv:  str,
    ontology_ttl: str,
    top_n:         int   = 200,
    threshold:     float = 0.5,
    sleep_seconds: float = 0.5,   # Wikidata asks for polite crawling
):
    """
    Main entity linking function.

    For each entity label in the KG:
      1. Query Wikidata Search API.
      2. If confidence >= threshold, add owl:sameAs to the Wikidata URI.
      3. Otherwise, classify as LocalPerson/Org/Place.

    Saves:
      - Aligned KG (Turtle)
      - Mapping CSV
      - Local ontology (Turtle)
    """
    print("Starting Wikidata entity linking...")

    os.makedirs(os.path.dirname(output_ttl),   exist_ok=True)
    os.makedirs(os.path.dirname(mapping_csv),  exist_ok=True)
    os.makedirs(os.path.dirname(ontology_ttl), exist_ok=True)

    g = Graph()
    g.parse(input_ttl, format="turtle")
    print(f"Graph loaded: {input_ttl} ({len(g)} triples)")

    add_local_classes(g)

    # Collect (entity_uri, label) pairs
    ent_pairs    = [(s, str(lbl)) for s, _, lbl in g.triples((None, RDFS.label, None))]
    label_counts = Counter(lbl for _, lbl in ent_pairs)
    SKIP_LABELS = {
    "announce", "attack", "claim", "defend", "deploy",
    "intervene in", "located in", "meet", "operate",
    "oppose", "support", "related to", "study",
    }

    top_labels = [
    label for label, _ in label_counts.most_common(top_n)
    if label.lower() not in SKIP_LABELS  # ← filtre ici
    ]
    print(f"Labels to process: {len(top_labels)}")

    # Build label -> set of local URIs
    label_to_uris = {}
    for uri, label in ent_pairs:
        label_to_uris.setdefault(label, set()).add(uri)

    rows    = []
    matched = 0

    for i, label in enumerate(top_labels, start=1):
        print(f"[{i}/{len(top_labels)}] Linking: {label}")

        ext_uri, conf = wikidata_lookup(label)
        time.sleep(sleep_seconds)

        if ext_uri and conf >= threshold:
            matched += 1
            for uri in label_to_uris[label]:
                g.add((uri, OWL.sameAs, URIRef(ext_uri)))
            rows.append([label, ext_uri, f"{conf:.2f}"])
        else:
            # Classify as local subclass
            for uri in label_to_uris[label]:
                if (uri, RDF.type, SCHEMA.Person) in g:
                    g.add((uri, RDF.type, EX.LocalPerson))
                elif (uri, RDF.type, SCHEMA.Organization) in g:
                    g.add((uri, RDF.type, EX.LocalOrganization))
                elif (uri, RDF.type, SCHEMA.Place) in g:
                    g.add((uri, RDF.type, EX.LocalPlace))
            rows.append([label, "", f"{conf:.2f}"])

    # Save outputs
    print("Writing mapping CSV...")
    with open(mapping_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Entity Label", "Wikidata URI", "Confidence"])
        writer.writerows(rows)

    print("Writing aligned KG...")
    g.serialize(output_ttl, format="turtle")

    print("Writing local ontology...")
    save_local_ontology(ontology_ttl)

    print(f"\nDone!")
    print(f"  Processed : {len(top_labels)} labels")
    print(f"  Matched   : {matched} (conf >= {threshold})")
    print(f"  Saved KG  : {output_ttl}")
    print(f"  Saved CSV : {mapping_csv}")