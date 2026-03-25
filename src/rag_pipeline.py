"""
rag_pipeline.py
=============

This script enables natural language question answering over an RDF knowledge graph (Turtle format),
using a Retrieval-Augmented Generation (RAG) pipeline based on SPARQL.

Workflow:
1. Load an RDF knowledge graph (.ttl) using rdflib
2. Build a schema summary (classes, predicates, sample triples)
3. Generate a SPARQL query from the user question using a local LLM (Ollama)
4. Execute the SPARQL query on the graph
5. (Optional) Repair the query if it fails
6. Generate a natural language answer grounded ONLY in the query results

Optimizations:
- Heuristic rules for simple questions (avoids LLM calls)
- Filtering of useful predicates (reduces Wikidata noise)
- Result size limits for performance
- Fully local LLM via Ollama (no external APIs)

Use cases:
- Question answering over knowledge graphs
- RDF data exploration
- Structured RAG demo (SPARQL + LLM)

Dependencies:
- rdflib
- requests
- Ollama (local LLM)

Optional environment variables:
- OLLAMA_URL
- OLLAMA_MODEL
- KG_TTL_FILE
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from rdflib.namespace import RDF, RDFS
import requests
from rdflib import Graph

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

MAX_PREDICATES = int(os.getenv("RAG_MAX_PREDICATES", "60"))
MAX_CLASSES = int(os.getenv("RAG_MAX_CLASSES", "30"))
SAMPLE_TRIPLES = int(os.getenv("RAG_SAMPLE_TRIPLES", "12"))
MAX_ROWS_TO_RETURN = int(os.getenv("RAG_MAX_ROWS", "20"))


def find_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_ttl_path(user_path: Optional[str] = None) -> Path:
    candidates: List[Path] = []

    if user_path:
        candidates.append(Path(user_path))

    env_path = os.getenv("KG_TTL_FILE")
    if env_path:
        candidates.append(Path(env_path))

    root = find_project_root()
    candidates.extend(
        [
            root / "data" / "raw" / "mykg_step4_expanded.ttl",
            root / "mykg_step4_expanded.ttl",
            root / "kg_artifacts" / "expanded.ttl",
            root / "data" / "mykg_step4_expanded.ttl",
        ]
    )

    for path in candidates:
        if path.exists():
            return path.resolve()

    raise FileNotFoundError(
        "Could not find the Turtle KG file. Pass --ttl /path/to/file.ttl "
        "or set KG_TTL_FILE."
    )


def ask_local_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 300,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    response = requests.post(ollama_url, json=payload, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"Ollama API error {response.status_code}: {response.text}")

    data = response.json()
    return data.get("response", "").strip()


def load_graph(ttl_path: str | Path) -> Graph:
    g = Graph()
    g.parse(str(ttl_path), format="turtle")
    return g


def get_prefix_block(g: Graph) -> str:
    allowed_prefixes = {"ex", "rdf", "rdfs", "owl", "xsd"}

    defaults = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "ex": "http://example.org/kg/",
    }

    ns_map = {p: str(ns) for p, ns in g.namespace_manager.namespaces() if p in allowed_prefixes}
    for k, v in defaults.items():
        ns_map.setdefault(k, v)

    lines = [f"PREFIX {p}: <{ns}>" for p, ns in sorted(ns_map.items())]
    return "\n".join(lines)

def list_distinct_predicates(g: Graph, limit: int = MAX_PREDICATES) -> List[str]:
    q = f"""
    SELECT DISTINCT ?p WHERE {{
      ?s ?p ?o .
    }}
    LIMIT {limit}
    """
    return [str(row.p) for row in g.query(q)]


def list_distinct_classes(g: Graph, limit: int = MAX_CLASSES) -> List[str]:
    q = f"""
    SELECT DISTINCT ?cls WHERE {{
      ?s a ?cls .
    }}
    LIMIT {limit}
    """
    return [str(row.cls) for row in g.query(q)]


def sample_triples(g: Graph, limit: int = SAMPLE_TRIPLES) -> List[Tuple[str, str, str]]:
    q = f"""
    SELECT ?s ?p ?o WHERE {{
      ?s ?p ?o .
    }}
    LIMIT {limit}
    """
    return [(str(r.s), str(r.p), str(r.o)) for r in g.query(q)]


def build_schema_summary(g: Graph) -> str:
    prefixes = get_prefix_block(g)
    
    # Filter useful predicates only — skip Wikidata internal props
    all_preds = list_distinct_predicates(g)
    useful_preds = [
        p for p in all_preds
        if "example.org/kg" in p  # nos prédicats locaux
        or p in [
            str(RDF.type),
            str(RDFS.label),
        ]
    ]
    
    clss    = list_distinct_classes(g)
    samples = sample_triples(g)
    
    # Show only local triples as examples (not Wikidata noise)
    local_samples = [
        (s, p, o) for s, p, o in samples
        if "example.org/kg" in s
    ]

    pred_lines   = "\n".join(f"- {p}" for p in useful_preds[:40])
    cls_lines    = "\n".join(f"- {c}" for c in clss[:20])
    sample_lines = "\n".join(f"- {s} {p} {o}" for s, p, o in local_samples[:10])

    return f"""
{prefixes}

# Local predicates (use these for SPARQL)
{pred_lines}

# Classes
{cls_lines}

# Example triples from local KG
{sample_lines}
""".strip()


def run_sparql(g: Graph, query: str) -> Tuple[List[str], List[Tuple[str, ...]]]:
    res = g.query(query)
    vars_ = [str(v) for v in res.vars]
    rows = [tuple(str(cell) for cell in r) for r in res]
    return vars_, rows


SPARQL_INSTRUCTIONS = """
You are a SPARQL generator for an RDF knowledge graph about Greenland and Arctic defense.

Convert the QUESTION into a valid SPARQL 1.1 SELECT query.

STRICT RULES:
- Use ONLY prefixes visible in the SCHEMA SUMMARY.
- Use ONLY predicates from the SCHEMA SUMMARY (ex:oppose, ex:support, ex:deploy...).
- Use ONLY known classes from the SCHEMA SUMMARY.
- Do NOT invent predicates, classes, or entity names.
- If an entity URI is uncertain, use FILTER(regex(str(?x), "...", "i")).
- Return ONLY one fenced code block labeled ```sparql
- No explanation outside the code block.

SPARQL SYNTAX RULES (strictly follow):
- Use && for AND conditions inside FILTER, NOT the word "AND"
- Use || for OR conditions inside FILTER, NOT the word "OR"  
- Multiple conditions: FILTER(?a > 0 && ?b < 10) not FILTER(?a > 0) AND FILTER(?b < 10)
- Never use SQL syntax in SPARQL

EXAMPLE 1:
Question: Who opposes Denmark?
```sparql
PREFIX ex: <http://example.org/kg/>
SELECT ?who WHERE {
  ?who ex:oppose ?x .
  FILTER(regex(str(?x), "denmark", "i"))
}
```

EXAMPLE 2:
Question: Who attacks NATO?
```sparql
PREFIX ex: <http://example.org/kg/>
SELECT ?who WHERE {
  ?who ex:attack ?x .
  FILTER(regex(str(?x), "nato", "i"))
}
```
"""


REPAIR_INSTRUCTIONS = """
The previous SPARQL query failed.

Using the SCHEMA SUMMARY and the ERROR MESSAGE:
- Fix the query.
- Use ONLY known prefixes / IRIs / predicates / classes from the summary.
- Keep it simple and robust.
- Return ONLY one fenced code block labeled ```sparql
"""

ANSWER_INSTRUCTIONS = """
You are a grounded question-answering assistant.

You are given:
1) the original user question
2) the SPARQL query used
3) the SPARQL result rows

Write a short natural-language answer grounded ONLY in the rows.
If there are no rows, say that the KG returned no result.
Do not invent facts.
"""


def make_sparql_prompt(schema_summary: str, question: str) -> str:
    return f"""{SPARQL_INSTRUCTIONS}

SCHEMA SUMMARY:
{schema_summary}

QUESTION:
{question}

Return only the SPARQL query in a fenced code block.
"""


def make_repair_prompt(
    schema_summary: str,
    question: str,
    bad_query: str,
    error_msg: str,
) -> str:
    return f"""{REPAIR_INSTRUCTIONS}

SCHEMA SUMMARY:
{schema_summary}

ORIGINAL QUESTION:
{question}

BAD SPARQL:
{bad_query}

ERROR MESSAGE:
{error_msg}

Return only the corrected SPARQL in a fenced code block.
"""


def make_grounded_answer_prompt(
    question: str,
    sparql_query: str,
    vars_: List[str],
    rows: List[Tuple[str, ...]],
) -> str:
    payload = {
        "question": question,
        "sparql_query": sparql_query,
        "variables": vars_,
        "rows": rows[:MAX_ROWS_TO_RETURN],
    }
    return f"""{ANSWER_INSTRUCTIONS}

DATA:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""


CODE_BLOCK_RE = re.compile(r"```(?:sparql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def extract_code_block(text: str) -> str:
    m = CODE_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def generate_sparql(
    question: str,
    schema_summary: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> str:
    raw = ask_local_llm(
        make_sparql_prompt(schema_summary, question),
        model=model,
        ollama_url=ollama_url,
    )
    return extract_code_block(raw)


def repair_sparql(
    schema_summary: str,
    question: str,
    bad_query: str,
    error_msg: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> str:
    raw = ask_local_llm(
        make_repair_prompt(schema_summary, question, bad_query, error_msg),
        model=model,
        ollama_url=ollama_url,
    )
    return extract_code_block(raw)


def answer_no_rag(
    question: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> str:
    prompt = f"Answer the following question as best as you can:\n\n{question}"
    return ask_local_llm(prompt, model=model, ollama_url=ollama_url)


def verbalize_rows_with_llm(
    question: str,
    sparql_query: str,
    vars_: List[str],
    rows: List[Tuple[str, ...]],
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> str:
    if not rows:
        return "I could not find any answer in the knowledge graph."

    prompt = f"""
You are a grounded assistant.

Your job:
- Write a short natural-language answer to the user's question.
- Use ONLY the SPARQL results below.
- Do NOT add any external knowledge.
- Do NOT guess.
- If the results are technical URIs, rewrite them in a readable way by using only their last path segment.
- Keep the answer concise, in 1 to 3 sentences maximum.

USER QUESTION:
{question}

SPARQL QUERY:
{sparql_query}

VARIABLES:
{vars_}

ROWS:
{rows[:10]}

Return only the final answer sentence(s), with no bullet points and no extra commentary.
"""
    return ask_local_llm(prompt, model=model, ollama_url=ollama_url)

def heuristic_sparql(question: str) -> str | None:
    q = question.strip().lower()

    # who opposes X
    if q.startswith("who opposes "):
        target = question.strip()[len("who opposes "):].strip(" ?")
        return f"""
PREFIX ex: <http://example.org/kg/>
SELECT ?who WHERE {{
  ?who ex:oppose ?x .
  FILTER(regex(str(?x), "{target}", "i"))
}}
LIMIT 20
""".strip()

    # what party is X in?
    if "party" in q and "trump" in q:
        return """
PREFIX ex: <http://example.org/kg/>
PREFIX ns1: <http://www.wikidata.org/prop/direct/>
SELECT ?party WHERE {
  <http://example.org/kg/person/donald_trump> ns1:P102 ?party .
}
LIMIT 5
""".strip()

    # what is X related to?
    if "related to" in q:
        target = q.replace("what is ", "").replace(" related to?", "").replace(" related to", "").strip()
        return f"""
PREFIX ex: <http://example.org/kg/>
SELECT ?o WHERE {{
  ?s ex:related_to ?o .
  FILTER(regex(str(?s), "{target}", "i"))
}}
LIMIT 20
""".strip()

    # who deploys / who attacks / who supports X
    for pred in ["deploy", "attack", "support", "defend", "meet", "claim"]:
        if f"who {pred}s " in q or f"who {pred}ed " in q:
            target = q.split(" ")[-1].strip(" ?")
            return f"""
PREFIX ex: <http://example.org/kg/>
SELECT ?who WHERE {{
  ?who ex:{pred} ?x .
  FILTER(regex(str(?x), "{target}", "i"))
}}
LIMIT 20
""".strip()

    # who is X / what is X
    if q.startswith("who is ") or q.startswith("what is "):
        target = question.split(" ", 2)[-1].strip(" ?")
        return f"""
PREFIX ex: <http://example.org/kg/>
SELECT ?p ?o WHERE {{
  ?s ?p ?o .
  FILTER(regex(str(?s), "{target}", "i"))
  FILTER(STRSTARTS(STR(?s), "http://example.org/kg/"))
}}
LIMIT 20
""".strip()

    # single entity name
    if len(q.split()) == 1:
        target = question.strip(" ?")
        return f"""
PREFIX ex: <http://example.org/kg/>
SELECT ?p ?o WHERE {{
  ?s ?p ?o .
  FILTER(regex(str(?s), "{target}", "i"))
  FILTER(STRSTARTS(STR(?s), "http://example.org/kg/"))
}}
LIMIT 20
""".strip()

    return None

def answer_with_sparql_generation(
    g: Graph,
    schema_summary: str,
    question: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    try_repair: bool = True,
) -> Dict[str, Any]:
    # 1) Try a deterministic heuristic first for simple/common questions
    heuristic_query = heuristic_sparql(question)

    if heuristic_query is not None:
        sparql = heuristic_query
        used_heuristic = True
    else:
        sparql = generate_sparql(
            question=question,
            schema_summary=schema_summary,
            model=model,
            ollama_url=ollama_url,
        )
        used_heuristic = False

    try:
        vars_, rows = run_sparql(g, sparql)
        grounded_answer = verbalize_rows_with_llm(
            question=question,
            sparql_query=sparql,
            vars_=vars_,
            rows=rows,
            model=model,
            ollama_url=ollama_url,
        )
        return {
            "query": sparql,
            "vars": vars_,
            "rows": rows,
            "repaired": False,
            "used_heuristic": used_heuristic,
            "error": None,
            "grounded_answer": grounded_answer,
        }

    except Exception as e:
        err = str(e)

        # If the heuristic query fails, do not try to "repair" it with the LLM.
        # Instead, fall back once to normal SPARQL generation.
        if used_heuristic:
            try:
                sparql = generate_sparql(
                    question=question,
                    schema_summary=schema_summary,
                    model=model,
                    ollama_url=ollama_url,
                )
                vars_, rows = run_sparql(g, sparql)
                grounded_answer = verbalize_rows_with_llm(
                    question=question,
                    sparql_query=sparql,
                    vars_=vars_,
                    rows=rows,
                    model=model,
                    ollama_url=ollama_url,
                )
                return {
                    "query": sparql,
                    "vars": vars_,
                    "rows": rows,
                    "repaired": False,
                    "used_heuristic": False,
                    "error": None,
                    "grounded_answer": grounded_answer,
                }
            except Exception as e2:
                err = str(e2)

        if not try_repair:
            return {
                "query": sparql,
                "vars": [],
                "rows": [],
                "repaired": False,
                "used_heuristic": used_heuristic,
                "error": err,
                "grounded_answer": None,
            }

        repaired = repair_sparql(
            schema_summary=schema_summary,
            question=question,
            bad_query=sparql,
            error_msg=err,
            model=model,
            ollama_url=ollama_url,
        )

        try:
            vars_, rows = run_sparql(g, repaired)
            grounded_answer = verbalize_rows_with_llm(
                question=question,
                sparql_query=repaired,
                vars_=vars_,
                rows=rows,
                model=model,
                ollama_url=ollama_url,
            )
            return {
                "query": repaired,
                "vars": vars_,
                "rows": rows,
                "repaired": True,
                "used_heuristic": False,
                "error": None,
                "grounded_answer": grounded_answer,
            }
        except Exception as e2:
            return {
                "query": repaired,
                "vars": [],
                "rows": [],
                "repaired": True,
                "used_heuristic": False,
                "error": str(e2),
                "grounded_answer": None,
            }
        

def pretty_print_result(result: Dict[str, Any]) -> None:
    print("\n[SPARQL Query Used]")
    print(result["query"])
    print("\n[Repaired?]", result["repaired"])

    if result.get("error"):
        print("\n[Execution Error]")
        print(result["error"])
        return

    print("\n[Grounded Answer]")
    print(result.get("grounded_answer") or "No answer generated.")

    vars_ = result.get("vars", [])
    rows = result.get("rows", [])

    if not rows:
        print("\n[No rows returned]")
        return

    print("\n[Results]")
    print(" | ".join(vars_))
    for r in rows[:MAX_ROWS_TO_RETURN]:
        print(" | ".join(r))
    if len(rows) > MAX_ROWS_TO_RETURN:
        print(f"... (showing {MAX_ROWS_TO_RETURN} of {len(rows)})")