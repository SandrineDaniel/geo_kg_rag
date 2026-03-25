"""
run_predicate_alignment.py
==========================
Script to align local KG predicates to standard ontology URIs.

Applies a two-strategy alignment: manual mapping first (primary),
then DBpedia SPARQL fallback for unmatched predicates.
Results are saved as owl:equivalentProperty triples in Turtle format,
with a CSV summary of all candidates for inspection.

Run with:
    python scripts/run_predicate_alignment.py

Input:
    outputs/graphs/mykg_step2_aligned.ttl

Output:
    outputs/graphs/predicate_alignment_step3.ttl
    outputs/mappings/predicate_candidates.csv
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.predicate_alignment import run_predicate_alignment

if __name__ == "__main__":
    run_predicate_alignment(
        input_ttl="outputs/graphs/mykg_step2_aligned.ttl",
        out_csv="outputs/mappings/predicate_candidates.csv",
        out_ttl="outputs/graphs/predicate_alignment_step3.ttl",
        top_predicates=30,
        examples_per_predicate=5,
        threshold_hits=3,
        sleep_seconds=0.2,
    )