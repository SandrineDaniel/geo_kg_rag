"""
run_stats.py
============
Generates descriptive statistics for the expanded Knowledge Graph.

Run AFTER run_sparql_expansion.py.

Input  : outputs/graphs/mykg_step4_expanded.ttl
Output : outputs/stats/kg_stats.json

Run with:
    python scripts/run_stats.py
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.stats import run_stats

if __name__ == "__main__":
    run_stats(
        input_ttl="outputs/graphs/mykg_step4_expanded.ttl",
        output_json="outputs/stats/kg_stats.json",
    )
    run_stats(input_ttl="outputs/graphs/mykg_step1_initial.ttl", output_json="outputs/stats/kg_stats_step1.json")