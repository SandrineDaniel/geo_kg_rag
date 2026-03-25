"""
kg_builder.py: Initial Knowledge Graph construction module.
===================

Reads the crawled JSONL file, applies NER and relation extraction,
and builds an RDF graph serialized in Turtle format.

For each article:
  1. Detects named entities (PERSON, ORG, GPE) using spaCy.
  2. Filters noise using is_good_entity() and corrects NER labels
     using correct_entity_label() (e.g. Trump misclassified as ORG).
  3. Creates RDF triples: entity to rdf:type to schema:Person/Org/Place
  4. Extracts subject-predicate-object relations between entities
     in the same sentence using extract_relations().
  5. Serializes the graph to Turtle (.ttl) format.

Used by:
  - scripts/run_kg_builder.py

Functions:
  - build_initial_kg()  : builds and serializes the RDF graph
  - print_graph_stats() : prints triple/entity/predicate counts
"""
import json
import os
import spacy
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD
from src.namespaces import EX, SCHEMA
from src.utils import (
    make_entity_uri,
    ner_label_to_class,
    is_good_entity,
    correct_entity_label,
)
from src.relations import extract_relations

nlp = spacy.load("en_core_web_lg")


def build_initial_kg(input_file: str, output_file: str):
    """Build the initial KG from the crawled JSONL file and save as Turtle.
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    g = Graph()
    g.bind("ex", EX)
    g.bind("schema", SCHEMA)
    g.bind("rdfs", RDFS)

    for line in open(input_file, "r", encoding="utf-8"):
        record = json.loads(line)
        url  = record.get("url", "")
        text = record.get("text", "") or ""

        if not text.strip():
            continue

        doc = nlp(text)

        # Local map: raw entity text to corrected NER label
        # Used to look up URIs when building relation triples
        entity_map = {}

        #  Entity extraction 
        for ent in doc.ents:
            if ent.label_ not in ("PERSON", "ORG", "GPE"):
                continue
            if not is_good_entity(ent.text):
                continue

            corrected_label = correct_entity_label(ent.text, ent.label_)
            u   = make_entity_uri(ent.text, corrected_label)
            cls = ner_label_to_class(corrected_label)

            g.add((u, RDF.type, cls))
            g.add((u, RDFS.label, Literal(ent.text)))

            if url:
                g.add((u, EX.sourceUrl, Literal(url, datatype=XSD.anyURI)))

            entity_map[ent.text.strip()] = corrected_label

        # Relation extraction w only keep relations where both subject and object are known entities
        for s, p, o in extract_relations(doc):
            if s not in entity_map or o not in entity_map:
                continue

            s_uri = make_entity_uri(s, entity_map[s])
            o_uri = make_entity_uri(o, entity_map[o])
            p_uri = EX[p]

            g.add((s_uri, p_uri, o_uri))
            g.add((p_uri, RDFS.label, Literal(p.replace("_", " "))))

    g.serialize(output_file, format="turtle")
    return g


def print_graph_stats(g: Graph):
    """Print basic statistics about the graph."""
    subjects   = set(s for s, _, _ in g)
    predicates = set(p for _, p, _ in g)
    objects    = set(o for _, _, o in g if isinstance(o, URIRef))

    print("Triples         :", len(g))
    print("Unique subjects :", len(subjects))
    print("Unique predicates:", len(predicates))
    print("Unique URI objects:", len(objects))