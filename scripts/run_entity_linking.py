import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.entity_linking import run_entity_linking

if __name__ == "__main__":
    run_entity_linking(
        input_ttl="outputs/graphs/mykg_step1_initial.ttl",
        output_ttl="outputs/graphs/mykg_step2_aligned.ttl",
        mapping_csv="outputs/mappings/mapping.csv",
        ontology_ttl="outputs/graphs/ontology_step2.ttl",
        top_n=200,
        threshold=0.25,
        sleep_seconds=0.1,
    )