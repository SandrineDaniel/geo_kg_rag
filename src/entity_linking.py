import os
import csv
import time
from collections import Counter

import requests
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL

from src.namespaces import EX, SCHEMA

DBP_LOOKUP = "https://lookup.dbpedia.org/api/search"

HEADERS = {
    "User-Agent": "KB-Lab-EntityLinking/1.0",
    "Accept": "application/json",
}


def _to_float_score(score):
    if score is None:
        return 0.0

    if isinstance(score, list):
        for x in score:
            try:
                return float(x)
            except (TypeError, ValueError):
                continue
        return 0.0

    try:
        return float(score)
    except (TypeError, ValueError):
        return 0.0


def dbpedia_lookup_json(label: str, max_hits: int = 5):
    """
    Returns (best_uri, conf01, raw_score) or (None, 0.0, 0.0)
    """
    params = {
        "query": label,
        "maxResults": str(max_hits),
        "format": "JSON",
    }

    try:
        response = requests.get(
            DBP_LOOKUP,
            params=params,
            headers=HEADERS,
            timeout=20,
        )
    except requests.RequestException:
        return None, 0.0, 0.0

    if response.status_code != 200 or not response.text.strip():
        return None, 0.0, 0.0

    try:
        data = response.json()
    except ValueError:
        return None, 0.0, 0.0

    docs = data.get("docs")
    if docs is None:
        docs = data.get("results")

    if not docs:
        return None, 0.0, 0.0

    best = docs[0]

    uri = best.get("resource") or best.get("uri")
    if isinstance(uri, list):
        uri = uri[0] if uri else None

    if not uri:
        return None, 0.0, 0.0

    score = best.get("score", 0.0)
    raw_score = _to_float_score(score)
    conf01 = raw_score / (raw_score + 10.0) if raw_score > 0 else 0.0

    return uri, conf01, raw_score


def add_local_classes(g: Graph):
    g.add((EX.LocalPerson, RDF.type, RDFS.Class))
    g.add((EX.LocalPerson, RDFS.subClassOf, SCHEMA.Person))

    g.add((EX.LocalOrganization, RDF.type, RDFS.Class))
    g.add((EX.LocalOrganization, RDFS.subClassOf, SCHEMA.Organization))

    g.add((EX.LocalPlace, RDF.type, RDFS.Class))
    g.add((EX.LocalPlace, RDFS.subClassOf, SCHEMA.Place))


def save_local_ontology(output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    onto = Graph()
    onto.bind("ex", EX)
    onto.bind("schema", SCHEMA)
    onto.bind("rdfs", RDFS)

    ontology_triples = [
        (EX.LocalPerson, RDF.type, RDFS.Class),
        (EX.LocalPerson, RDFS.subClassOf, SCHEMA.Person),
        (EX.LocalOrganization, RDF.type, RDFS.Class),
        (EX.LocalOrganization, RDFS.subClassOf, SCHEMA.Organization),
        (EX.LocalPlace, RDF.type, RDFS.Class),
        (EX.LocalPlace, RDFS.subClassOf, SCHEMA.Place),
    ]

    for triple in ontology_triples:
        onto.add(triple)

    onto.serialize(output_path, format="turtle")


def run_entity_linking(
    input_ttl: str,
    output_ttl: str,
    mapping_csv: str,
    ontology_ttl: str,
    top_n: int = 20,
    threshold: float = 0.25,
    sleep_seconds: float = 0.1,
):
    print("Starting entity linking...")

    os.makedirs(os.path.dirname(output_ttl), exist_ok=True)
    os.makedirs(os.path.dirname(mapping_csv), exist_ok=True)
    os.makedirs(os.path.dirname(ontology_ttl), exist_ok=True)

    g = Graph()
    g.parse(input_ttl, format="turtle")
    print("Graph loaded:", input_ttl)

    add_local_classes(g)

    ent_pairs = [(s, str(lbl)) for s, _, lbl in g.triples((None, RDFS.label, None))]
    label_counts = Counter(lbl for _, lbl in ent_pairs)

    top_labels = [label for label, _ in label_counts.most_common(top_n)]
    print("Labels to process:", len(top_labels))

    label_to_uris = {}
    for uri, label in ent_pairs:
        label_to_uris.setdefault(label, set()).add(uri)

    rows = []
    matched = 0

    for i, label in enumerate(top_labels, start=1):
        print(f"[{i}/{len(top_labels)}] Linking: {label}")

        ext_uri, conf, raw_score = dbpedia_lookup_json(label)
        time.sleep(sleep_seconds)

        if ext_uri and conf >= threshold:
            matched += 1
            for uri in label_to_uris[label]:
                g.add((uri, OWL.sameAs, URIRef(ext_uri)))

            rows.append([label, ext_uri, f"{conf:.3f}", f"{raw_score:.3f}"])
        else:
            for uri in label_to_uris[label]:
                if (uri, RDF.type, SCHEMA.Person) in g:
                    g.add((uri, RDF.type, EX.LocalPerson))
                elif (uri, RDF.type, SCHEMA.Organization) in g:
                    g.add((uri, RDF.type, EX.LocalOrganization))
                elif (uri, RDF.type, SCHEMA.Place) in g:
                    g.add((uri, RDF.type, EX.LocalPlace))

            rows.append([label, "", f"{conf:.3f}", f"{raw_score:.3f}"])

    print("Writing mapping CSV...")
    with open(mapping_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Private Entity (label)", "External URI", "Confidence", "RawScore"])
        writer.writerows(rows)

    print("Writing aligned KG...")
    g.serialize(output_ttl, format="turtle")

    print("Writing local ontology...")
    save_local_ontology(ontology_ttl)

    print("Done.")
    print("Processed labels:", len(top_labels))
    print(f"Matched (conf>={threshold:.2f}):", matched)
    print("Saved:", output_ttl)
    print("Saved:", mapping_csv)
    print("Saved ontology:", ontology_ttl)