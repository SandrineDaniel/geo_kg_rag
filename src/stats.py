"""
stats.py:
===================
Computes and saves descriptive statistics about the Knowledge Graph.

Metrics computed:
  - Total number of triples
  - Number of unique subjects, predicates, objects
  - Number of entities per type (Person, Organization, Place)
  - Number of owl:sameAs links (entity linking coverage)
  - Number of owl:equivalentProperty links (predicate alignment coverage)
  - Top 10 most frequent predicates
  - Top 10 most mentioned entities (by outgoing degree)
"""

import json
import os
from collections import Counter

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL
from src.namespaces import EX, SCHEMA


def compute_stats(g: Graph) -> dict:
    """
    Compute all KG statistics and return them as a dictionary.
    """
    triples = list(g)
    total = len(triples)

    # Basic counts
    subjects   = {s for s, _, _ in triples if isinstance(s, URIRef)}
    predicates = {p for _, p, _ in triples}
    objects    = {o for _, _, o in triples if isinstance(o, URIRef)}

    # Entity type counts
    persons = sum(1 for _, _, o in g.triples((None, RDF.type, SCHEMA.Person)))
    orgs    = sum(1 for _, _, o in g.triples((None, RDF.type, SCHEMA.Organization)))
    places  = sum(1 for _, _, o in g.triples((None, RDF.type, SCHEMA.Place)))

    # Linking and alignment coverage
    sameas_links   = sum(1 for _ in g.triples((None, OWL.sameAs, None)))
    equiv_props    = sum(1 for _ in g.triples((None, OWL.equivalentProperty, None)))

    # Top 10 most frequent predicates (excluding metadata predicates)
    meta = {str(RDF.type), str(RDFS.label), str(OWL.sameAs), str(EX.sourceUrl)}
    pred_counter = Counter(
        str(p) for _, p, _ in triples if str(p) not in meta
    )
    top_predicates = pred_counter.most_common(10)

    # Top 10 most connected entities (by number of outgoing triples)
    subj_counter = Counter(
        str(s) for s, p, _ in triples
        if isinstance(s, URIRef) and str(p) not in meta
    )
    top_entities = subj_counter.most_common(10)

    return {
        "total_triples": total,
        "unique_subjects": len(subjects),
        "unique_predicates": len(predicates),
        "unique_uri_objects": len(objects),
        "entity_types": {
            "Person": persons,
            "Organization": orgs,
            "Place": places,
        },
        "owl_sameAs_links": sameas_links,
        "owl_equivalentProperty_links": equiv_props,
        "top_10_predicates": [
            {"predicate": p, "count": c} for p, c in top_predicates
        ],
        "top_10_entities_by_degree": [
            {"entity": e, "outgoing_triples": c} for e, c in top_entities
        ],
    }


def print_stats(stats: dict):
    """Pretty-print the stats to stdout."""
    print("\n" + "=" * 55)
    print("  KNOWLEDGE GRAPH STATISTICS")
    print("=" * 55)
    print(f"  Total triples          : {stats['total_triples']:,}")
    print(f"  Unique subjects        : {stats['unique_subjects']:,}")
    print(f"  Unique predicates      : {stats['unique_predicates']:,}")
    print(f"  Unique URI objects     : {stats['unique_uri_objects']:,}")
    print(f"  owl:sameAs links       : {stats['owl_sameAs_links']:,}")
    print(f"  owl:equivalentProperty : {stats['owl_equivalentProperty_links']:,}")
    print()
    print("  Entity types:")
    for etype, count in stats["entity_types"].items():
        print(f"    {etype:<16}: {count:,}")
    print()
    print("  Top 10 predicates:")
    for item in stats["top_10_predicates"]:
        short = item["predicate"].split("/")[-1]
        print(f"    {short:<30} {item['count']:>5}")
    print()
    print("  Top 10 entities by degree:")
    for item in stats["top_10_entities_by_degree"]:
        short = item["entity"].split("/")[-1]
        print(f"    {short:<30} {item['outgoing_triples']:>5} triples")
    print("=" * 55)


def save_stats(stats: dict, output_path: str):
    """Save stats as a JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"\nStats saved to: {output_path}")


def run_stats(input_ttl: str, output_json: str):
    """Load a TTL graph, compute stats, print and save them."""
    g = Graph()
    g.parse(input_ttl, format="turtle")
    stats = compute_stats(g)
    print_stats(stats)
    save_stats(stats, output_json)
    return stats