"""
run_sparql_expansion.py
=======================
Script to run SPARQL-based 1-hop expansion of the Knowledge Graph.

Input  : outputs/graphs/mykg_step2_aligned.ttl  (entity-linked KG)
Output : outputs/graphs/mykg_step4_expanded.ttl  (enriched KG)

Run with:
    python scripts/run_sparql_expansion.py
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.sparql_expansion import run_sparql_expansion

if __name__ == "__main__":
    run_sparql_expansion(
        input_ttl="outputs/graphs/mykg_step2_aligned.ttl",
        output_ttl="outputs/graphs/mykg_step4_expanded.ttl",
        max_triples=100_000,
        per_entity_limit=1_000,
        sleep_seconds=0.2,
    )