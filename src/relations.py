import spacy

nlp = spacy.load("en_core_web_lg")

BAD_RELATIONS = {
    "say", "tell", "report", "announce", "add", "declare",
    "explain", "note", "state", "mention", "according"
}


def extract_relations(doc):
    """Extracts relations between named entities in a given spaCy document."""
    relations = []

    for sent in doc.sents:
        ents = [ent for ent in sent.ents if ent.label_ in ["PERSON", "ORG", "GPE", "DATE"]] # Filter entities to only include relevant types

        if len(ents) >= 2:
            root_verbs = [
                token.lemma_.lower()
                for token in sent
                if token.dep_ == "ROOT" and token.pos_ == "VERB" # Focus on verbs as potential relations
            ]

            relation = root_verbs[0] if root_verbs else "related_to"

            if relation in BAD_RELATIONS:
                continue
            if len(relation) < 3:
                continue
            if ents[0].text == ents[1].text:
                continue

            relations.append((ents[0].text, relation, ents[1].text))

    return relations