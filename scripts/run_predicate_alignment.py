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