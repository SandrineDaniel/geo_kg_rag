"""
run_kg_builder.py
=================
Script to build the initial Knowledge Graph from crawled data.

Reads the cleaned JSONL file, applies NER and relation extraction,
and serializes the resulting RDF graph in Turtle format.
Prints basic graph statistics (triples, entities, predicates) on completion.

Run with:
    python scripts/run_kg_builder.py

Input:
    data/raw/crawler_output.jsonl

Output:
    outputs/graphs/mykg_step1_initial.ttl
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.kg_builder import build_initial_kg, print_graph_stats

g = build_initial_kg(
    input_file="data/raw/crawler_output.jsonl",
    output_file="outputs/graphs/mykg_step1_initial.ttl"
)

print_graph_stats(g)