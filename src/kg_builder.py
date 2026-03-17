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
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    g = Graph()
    g.bind("ex", EX)
    g.bind("schema", SCHEMA)
    g.bind("rdfs", RDFS)

    for line in open(input_file, "r", encoding="utf-8"):
        record = json.loads(line)
        url = record.get("url", "")
        text = record.get("text", "") or ""

        if not text.strip():
            continue

        doc = nlp(text)

        # mapping local texte -> label corrected 
        entity_map = {}

        # entities
        for ent in doc.ents:
            if ent.label_ not in ("PERSON", "ORG", "GPE"):
                continue

            if not is_good_entity(ent.text):
                continue

            corrected_label = correct_entity_label(ent.text, ent.label_)
            u = make_entity_uri(ent.text, corrected_label)
            cls = ner_label_to_class(corrected_label)

            g.add((u, RDF.type, cls))
            g.add((u, RDFS.label, Literal(ent.text)))

            if url:
                g.add((u, EX.sourceUrl, Literal(url, datatype=XSD.anyURI)))

            entity_map[ent.text.strip()] = corrected_label

        # relations
        triples = extract_relations(doc)
        for s, p, o in triples:
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
    triples_count = len(g)
    subjects = set(s for s, _, _ in g)
    predicates = set(p for _, p, _ in g)
    objects = set(o for _, _, o in g if isinstance(o, URIRef))

    print("Triples:", triples_count)
    print("Unique subjects:", len(subjects))
    print("Unique predicates:", len(predicates))
    print("Unique URI objects:", len(objects))