"""
run_entity_linking.py
=====================

Script to run entity linking on the initial Knowledge Graph.

Queries the DBpedia Lookup API for each entity label in the KG
and adds owl:sameAs triples for confident matches (conf >= 0.25).
Unmatched entities are classified as LocalPerson/Org/Place.
Also generates the local ontology file.

Run with:
    python scripts/run_entity_linking.py

Input:
    outputs/graphs/mykg_step1_initial.ttl

Output:
    outputs/graphs/mykg_step2_aligned.ttl
    outputs/graphs/ontology_step2.ttl
    outputs/mappings/mapping.csv
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.entity_linking import add_core_entities, run_entity_linking

if __name__ == "__main__":
    # Add core entities BEFORE entity linking
    add_core_entities("outputs/graphs/mykg_step1_initial.ttl")
    run_entity_linking(
        input_ttl="outputs/graphs/mykg_step1_initial.ttl",
        output_ttl="outputs/graphs/mykg_step2_aligned.ttl",
        mapping_csv="outputs/mappings/mapping.csv",
        ontology_ttl="outputs/graphs/ontology_step2.ttl",
        top_n=300,
        threshold=0.25,
        sleep_seconds=1,
    )