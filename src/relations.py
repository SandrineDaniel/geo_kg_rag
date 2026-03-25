"""
relations.py:  relation extraction module.
===================


Extracts (subject, predicate, object) triples from spaCy-parsed text.
For each sentence containing at least 2 named entities (PERSON, ORG, GPE),
the ROOT verb is used as the relation between the first two entities.

Relation normalization:
  - Generic/uninformative verbs (be, have, say...) are discarded because noise.
  - Domain-specific verbs are mapped to canonical relation names
  - Weak relations (write_about, welcome, buy) are filtered out.

Used by:
  - kg_builder.py : extract_relations()
  - utils.py      : extract_sentence_relations() (baseline version)

Functions:
  - normalize_relation() : maps a verb lemma to a canonical relation name
  - extract_relations()  : extracts all triples from a spaCy Doc
"""

import spacy

nlp = spacy.load("en_core_web_lg")

# Entity types considered valid for relation extraction
VALID_ENTITY_LABELS = {"PERSON", "ORG", "GPE"}

# Verbs that are too generic to be meaningful relations
BAD_RELATIONS = {
    "be", "have", "do", "say", "tell", "report", "announce", "add",
    "mention", "note", "state", "list", "make", "take", "come", "go",
    "think", "believe", "want", "consider", "include", "point", "mark",
    "set", "stand", "continue", "finish", "end", "focus", "drive",
}

# Maps verb lemmas to canonical relation names in our KG
# Grouped by semantic category for readability
RELATION_MAP = {
    # Support / defense
    "support":   "support",
    "back":      "support",
    "defend":    "defend",
    "protect":   "defend",
    # Military / deployment
    "deploy":    "deploy",
    "send":      "deploy",
    "operate":   "operate",
    "attack":    "attack",
    "destroy":   "attack",
    "intervene": "intervene_in",
    # Opposition
    "slam":      "oppose",
    "oppose":    "oppose",
    "refuse":    "oppose",
    "ignore":    "oppose",
    # Diplomatic
    "meet":      "meet",
    "claim":     "claim",
    "issue":     "announce",
    # Geographic
    "locate":    "located_in",
    # Other
    "write":     "write_about",
    "study":     "study",
    "buy":       "buy",
    "welcome":   "welcome",
    "related_to":"related_to",
}

# Relations considered too weak or uninformative for the KG
WEAK_RELATIONS = {"write_about", "welcome", "buy"}


def normalize_relation(verb: str) -> str | None:
    """
    Map a verb lemma to a canonical relation name.
    Returns None if the verb is too generic or not in the relation map.
    """
    verb = verb.lower().strip()
    if verb in BAD_RELATIONS:
        return None
    return RELATION_MAP.get(verb, None)


def extract_relations(doc) -> list[tuple[str, str, str]]:
    """
    Extract (subject, predicate, object) triples from a spaCy Doc.

    Strategy:
      - For each sentence with >= 2 named entities,
        use the ROOT verb as the relation.
      - Skip sentences with no ROOT verb, generic verbs, or weak relations.
      - Skip self-relations (subject == object).

    Returns a list of (subject_text, relation_name, object_text) tuples.
    """
    triples = []

    for sent in doc.sents:
        ents = [ent for ent in sent.ents if ent.label_ in VALID_ENTITY_LABELS]

        if len(ents) < 2:
            continue

        # Extract the ROOT verb lemma of the sentence
        root_verbs = [
            token.lemma_.lower()
            for token in sent
            if token.dep_ == "ROOT" and token.pos_ == "VERB"
        ]

        raw_relation = root_verbs[0] if root_verbs else "related_to"
        relation = normalize_relation(raw_relation)

        if relation is None or relation in WEAK_RELATIONS:
            continue

        subject = ents[0].text.strip()
        obj     = ents[1].text.strip()

        if subject == obj:
            continue

        triples.append((subject, relation, obj))

    return triples