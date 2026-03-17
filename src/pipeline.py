import json
import csv
from extraction import nlp
from relations import extract_relations


def extract_triples(input_file, output_file):
    """Extracts subject-predicate-object triples from the text in the input JSONL file and saves them to a CSV file."""
    with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["subject", "predicate", "object", "source_url"])

        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                url = record["url"]
                doc = nlp(record["text"])

                triples = extract_relations(doc)

                for s, p, o in triples:
                    writer.writerow([s, p, o, url])