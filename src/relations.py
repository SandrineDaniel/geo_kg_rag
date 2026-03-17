import spacy

nlp = spacy.load("en_core_web_lg")

VALID_ENTITY_LABELS = {"PERSON", "ORG", "GPE"}

BAD_RELATIONS = {
    "be", "have", "do", "say", "tell", "report", "announce", "add",
    "mention", "note", "state", "list", "make", "take", "come", "go",
    "think", "believe", "want", "consider", "include", "point", "mark",
    "set", "stand", "continue", "finish", "end", "focus", "drive"
}

RELATION_MAP = {
    "support": "support",
    "back": "support",
    "defend": "defend",
    "protect": "defend",
    "deploy": "deploy",
    "send": "deploy",
    "operate": "operate",
    "attack": "attack",
    "destroy": "attack",
    "slam": "oppose",
    "oppose": "oppose",
    "refuse": "oppose",
    "ignore": "oppose",
    "claim": "claim",
    "issue": "announce",
    "welcome": "welcome",
    "meet": "meet",
    "buy": "buy",
    "locate": "located_in",
    "write": "write_about",
    "study": "study",
    "intervene": "intervene_in",
    "related_to": "related_to",
}


def normalize_relation(verb: str) -> str | None:
    verb = verb.lower().strip()

    if verb in BAD_RELATIONS:
        return None

    return RELATION_MAP.get(verb, None)


def extract_relations(doc):
    triples = []

    for sent in doc.sents:
        ents = [ent for ent in sent.ents if ent.label_ in VALID_ENTITY_LABELS]

        if len(ents) < 2:
            continue

        root_verbs = [
            token.lemma_.lower()
            for token in sent
            if token.dep_ == "ROOT" and token.pos_ == "VERB"
        ]

        raw_relation = root_verbs[0] if root_verbs else "related_to"
        relation = normalize_relation(raw_relation)

        if relation is None:
            continue
        WEAK_RELATIONS = {"write_about", "welcome", "buy"}

        if relation in WEAK_RELATIONS:
            continue

        subject = ents[0].text.strip()
        obj = ents[1].text.strip()

        if subject == obj:
            continue

        triples.append((subject, relation, obj))

    return triples