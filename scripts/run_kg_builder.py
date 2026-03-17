import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.kg_builder import build_initial_kg, print_graph_stats

g = build_initial_kg(
    input_file="data/raw/crawler_output.jsonl",
    output_file="outputs/graphs/mykg_step1_initial.ttl"
)

print_graph_stats(g)