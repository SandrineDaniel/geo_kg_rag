"""
run_rag.py
=======================

This script is the command-line interface for the RDF/SPARQL RAG pipeline.
It loads a Turtle knowledge graph, builds a schema summary, and lets you ask
questions either interactively or through a single CLI argument.

What this script does:
1. Resolves the path to the Turtle knowledge graph (.ttl)
2. Loads the RDF graph with rdflib
3. Builds a schema summary from the graph
4. Sends the user question to:
   - a baseline local LLM answer without RAG
   - a SPARQL-based RAG pipeline that generates and executes a query
5. Prints the grounded answer and returned rows

Modes:
- Single-question mode:
  Run once with --question and exit
- Interactive mode:
  Start a prompt loop and ask multiple questions until 'quit' or 'exit'

Requirements:
- Python 3.10+
- rdflib
- requests
- Ollama installed and running locally
- A pulled local model such as llama3.2:1b
- A Turtle knowledge graph file (.ttl)

Python dependencies:
    pip install rdflib requests

Ollama setup:
1. Install Ollama:
       https://ollama.com/download

2. Start the Ollama server:
       ollama serve

3. Pull the model used by the script:
       ollama pull llama3.2:1b

4. Optional test:
       ollama run llama3.2:1b

Default execution:
    python scripts/run_rag.py --ttl outputs/graphs/mykg_step4_expanded.ttl --model llama3.2:1b

Single-question mode:
    python scripts/run_rag.py \
        --ttl outputs/graphs/mykg_step4_expanded.ttl \
        --model llama3.2:1b \
        --question "Who opposes Denmark?"

Interactive mode:
    python scripts/run_rag.py \
        --ttl outputs/graphs/mykg_step4_expanded.ttl \
        --model llama3.2:1b

Notes:
- The baseline answer uses the local LLM directly, without graph retrieval
- The RAG answer generates SPARQL, queries the graph, and answers only from returned results
- If SPARQL generation fails, the pipeline can try to repair the query
- Type 'quit' or 'exit' in interactive mode to stop the program
"""

from __future__ import annotations
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import argparse

from src.rag_pipeline import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    answer_no_rag,
    answer_with_sparql_generation,
    build_schema_summary,
    load_graph,
    pretty_print_result,
    resolve_ttl_path,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CLI RAG over RDF/SPARQL")
    parser.add_argument("--ttl", type=str, default="outputs/graphs/mykg_step4_expanded.ttl", help="Path to Turtle KG file")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--ollama-url", type=str, default=DEFAULT_OLLAMA_URL, help="Ollama API URL")
    parser.add_argument("--question", type=str, default=None, help="Ask one question and exit")
    args = parser.parse_args()

    ttl_path = resolve_ttl_path(args.ttl)
    print(f"Using KG: {ttl_path}")

    g = load_graph(ttl_path)
    print(f"Loaded {len(g)} triples.")

    schema = build_schema_summary(g)

    if args.question:
        print("\n--- Baseline (No RAG) ---")
        try:
            print(answer_no_rag(args.question, model=args.model, ollama_url=args.ollama_url))
        except Exception as e:
            print(f"Baseline failed: {e}")

        print("\n--- SPARQL-generation RAG ---")
        result = answer_with_sparql_generation(
            g=g,
            schema_summary=schema,
            question=args.question,
            model=args.model,
            ollama_url=args.ollama_url,
            try_repair=True,
        )
        pretty_print_result(result)
        return

    while True:
        q = input("\nQuestion (or 'quit'): ").strip()
        if q.lower() in {"quit", "exit"}:
            break

        print("\n--- Baseline (No RAG) ---")
        try:
            print(answer_no_rag(q, model=args.model, ollama_url=args.ollama_url))
        except Exception as e:
            print(f"Baseline failed: {e}")

        print("\n--- SPARQL-generation RAG ---")
        result = answer_with_sparql_generation(
            g=g,
            schema_summary=schema,
            question=q,
            model=args.model,
            ollama_url=args.ollama_url,
            try_repair=True,
        )
        pretty_print_result(result)


if __name__ == "__main__":
    main()