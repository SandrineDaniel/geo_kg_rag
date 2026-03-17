import spacy
import json
import csv

nlp = spacy.load("en_core_web_lg")

#NER only for PERSON, ORG, GPE, DATE with a minimum length of 3 characters to avoid noise.
def extract_entities(input_file, output_file):
    """Extracts named entities from the text in the input JSONL file and saves them to a CSV file."""
    with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["entity", "type", "source_url"])

        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                url = record["url"]
                doc = nlp(record["text"])

                for ent in doc.ents:
                    if ent.label_ in ["PERSON", "ORG", "GPE", "DATE"]:
                        if len(ent.text) > 2:
                            writer.writerow([ent.text, ent.label_, url])