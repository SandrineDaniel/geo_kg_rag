"""
sparql_expansion.py
===================
Expands the local Knowledge Graph by fetching 1-hop DBpedia triples
for every entity that was linked via owl:sameAs during entity linking.

What is SPARQL?
---------------
SPARQL (SPARQL Protocol and RDF Query Language) is the standard query
language for RDF graphs, analogous to SQL for relational databases.
A basic SPARQL query looks like:
    SELECT ?p ?o WHERE { <entity> ?p ?o . }
This returns all (predicate, object) pairs for a given subject entity.

Why expand with DBpedia?
------------------------
After entity linking, each local entity (e.g. ex:person/trump) has an
owl:sameAs link to a DBpedia resource (e.g. dbpedia:Donald_Trump).
DBpedia contains rich encyclopedic facts about these entities.
By fetching their 1-hop neighbourhood from DBpedia and adding those
triples to our graph, we enrich the KG with background knowledge
that was not present in our original news corpus.

We restrict fetched predicates to the DBpedia Ontology namespace
(http://dbpedia.org/ontology/) to avoid noisy administrative triples
(Wikipedia links, categories, etc.).
"""

import time
import requests
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import OWL

# ── Namespaces ────────────────────────────────────────────────────────────────
EX = Namespace("http://example.org/kg/")
DBO = Namespace("http://dbpedia.org/ontology/")

# ── DBpedia public SPARQL endpoint ────────────────────────────────────────────
DBP_ENDPOINT = "https://dbpedia.org/sparql"

HEADERS = {"User-Agent": "KB-Lab-Expansion/1.0"}


def query_dbpedia(query: str) -> dict:
    """
    Send a SPARQL SELECT query to the DBpedia public endpoint.
    Returns the parsed JSON response.
    Raises requests.HTTPError on non-2xx responses.
    """
    r = requests.get(
        DBP_ENDPOINT,
        params={"query": query, "format": "application/sparql-results+json"},
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def expand_one_hop(entity_uri: str, per_entity_limit: int) -> list:
    """
    Fetch all (predicate, object) pairs for a given DBpedia entity URI,
    restricted to DBpedia Ontology predicates to keep results clean.

    Example SPARQL sent:
        SELECT ?p ?o WHERE {
          <http://dbpedia.org/resource/Donald_Trump> ?p ?o .
          FILTER(STRSTARTS(STR(?p), "http://dbpedia.org/ontology/"))
        } LIMIT 1000
    """
    query = f"""
    SELECT ?p ?o WHERE {{
      <{entity_uri}> ?p ?o .
      FILTER(STRSTARTS(STR(?p), "http://dbpedia.org/ontology/"))
    }}
    LIMIT {per_entity_limit}
    """
    return query_dbpedia(query)["results"]["bindings"]


def collect_aligned_entities(g: Graph) -> set:
    """
    Extract all DBpedia resource URIs that are linked from our local KG
    via owl:sameAs triples.
    These are the entities we will expand.
    """
    return {
        str(o)
        for _, _, o in g.triples((None, OWL.sameAs, None))
        if str(o).startswith("http://dbpedia.org/resource/")
    }


def run_sparql_expansion(
    input_ttl: str,
    output_ttl: str,
    max_triples: int = 100_000,
    per_entity_limit: int = 1_000,
    sleep_seconds: float = 0.2,
) -> dict:
    """
    Main expansion function.

    For each DBpedia entity linked in the KG (via owl:sameAs):
      1. Query DBpedia for its 1-hop DBO neighbourhood.
      2. Add the returned triples to the local graph.
      3. Stop early if the graph reaches max_triples.

    Returns a stats dict with counts for the final report.
    """
    # Load the aligned KG (output of step 2)
    g = Graph()
    g.parse(input_ttl, format="turtle")
    initial_triples = len(g)
    print(f"Loaded graph: {initial_triples} triples")

    # Identify entities to expand
    aligned = collect_aligned_entities(g)
    print(f"Aligned DBpedia entities to expand: {len(aligned)}")

    expanded_count = 0
    failed_count = 0
    added_total = 0

    for dbp_entity in aligned:
        # Safety cap: stop if we reach the maximum graph size
        if len(g) >= max_triples:
            print(f"Reached max_triples cap ({max_triples}), stopping.")
            break

        try:
            results = expand_one_hop(dbp_entity, per_entity_limit)
        except Exception as e:
            print(f"  ⚠ Failed to expand {dbp_entity}: {e}")
            failed_count += 1
            continue

        added_here = 0
        for row in results:
            p = URIRef(row["p"]["value"])
            o_val = row["o"]

            # Handle both URI objects and literal objects
            if o_val["type"] == "uri":
                o = URIRef(o_val["value"])
            else:
                o = Literal(o_val["value"])

            g.add((URIRef(dbp_entity), p, o))
            added_here += 1

            if len(g) >= max_triples:
                break

        added_total += added_here
        expanded_count += 1
        print(f"  ✓ {dbp_entity.split('/')[-1]} → +{added_here} triples (total: {len(g)})")
        time.sleep(sleep_seconds)

    # Serialize the expanded graph
    g.serialize(output_ttl, format="turtle")

    stats = {
        "initial_triples": initial_triples,
        "final_triples": len(g),
        "added_triples": added_total,
        "entities_expanded": expanded_count,
        "entities_failed": failed_count,
        "entities_total": len(aligned),
    }

    print(f"\nExpansion complete.")
    print(f"  Triples before : {initial_triples}")
    print(f"  Triples added  : {added_total}")
    print(f"  Triples after  : {len(g)}")
    print(f"  Saved to       : {output_ttl}")

    return stats