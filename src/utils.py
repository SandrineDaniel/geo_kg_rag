"""
utils.py: Utility functions shared across the pipeline.
===================
Used by:
  - kg_builder.py    : make_entity_uri, ner_label_to_class, is_good_entity, correct_entity_label
  - relations.py     : slugify, extract_sentence_relations
  - entity_linking.py: (indirectly via kg_builder)

Contents:
  - Entity noise filtering : looks_like_noise, is_good_entity
  - Label correction       : correct_entity_label (fixes NER misclassifications)
  - URI helpers            : slugify, make_entity_uri, ner_label_to_class
  - Baseline relation      : extract_sentence_relations
"""

import re
import unicodedata
from rdflib import URIRef
from src.namespaces import EX, SCHEMA


# Noise filter lists: 

# Substrings typical of Spanish cookie banners and UI noise
# (some crawled pages were partly in Spanish like El pais)
BAD_ENTITY_SUBSTRINGS = {
    "cuenta", "contraseña", "premium", "suscripción", "cookies",
    "usuario", "dispositivo", "lectura", "términos", "condiciones",
    "compartir", "compartiendo", "contratar", "personalizar",
    "aquí", "aqui", "podrás", "podras", "mensaje",
    "vuestra experiencia", "el país usa edition", "usa edition",
}

# Exact strings that are too generic or clearly not real entities
BAD_EXACT_ENTITIES = {
    "cada", "davos", "militarily", "defence", "government",
    "house", "forum", "frontpage",
    # Partial names or fragments that caused NER false positives
    "cambia tu", "demark", "leyen", "nielsen", "mette",
    "farage", "frederiksen", "miller", "ciobanu", "rostrup",
}

# Known person names that areused to correct NER misclassifications (e.g. ORG → PERSON)
PERSON_HINTS = {
    "trump", "macron", "putin", "frederiksen", "rutte", "zelenskiy",
    "biden", "rubio", "vance", "milei", "meloni", "merz",
}

# Keywords suggesting an entity is an organization
ORG_HINTS = {
    "nato", "government", "ministry", "department", "house",
    "institute", "university", "commission", "force", "post",
    "times", "guardian", "cnn", "pentagon",
}

# Known geopolitical places — used to correct GPE misclassifications
GPE_HINTS = {
    "greenland", "denmark", "washington", "nuuk", "copenhagen",
    "russia", "china", "ukraine", "alaska", "iceland", "norway",
    "the united states", "u.s.", "usa",
}


# Label correction 

def correct_entity_label(text: str, predicted_label: str) -> str:
    """
    Correct spaCy NER misclassifications using domain knowledge.
    Examples of errors fixed: 
      - 'Trump' predicted as ORG is corrected to PERSON
      - 'Greenland' predicted as PERSON is corrected to GPE
      - 'NATO' predicted as PERSON is corrected to ORG
    """
    t = text.strip().lower()

    if any(name in t for name in PERSON_HINTS):
        return "PERSON"

    if any(word in t for word in ORG_HINTS):
        return "ORG"

    if t in GPE_HINTS:
        return "GPE"

    return predicted_label


#URI helpers 

def slugify(text: str) -> str:
    """
    Convert a text string into a URL-safe slug.
    Example: 'Donald Trump' to 'donald_trump'
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def make_entity_uri(ent_text: str, ent_label: str) -> URIRef:
    """
    Build a local RDF URI for an entity.
    Example: ('Donald Trump', 'PERSON') to ex:person/donald_trump
    """
    kind_map = {
        "PERSON": "person",
        "ORG":    "org",
        "GPE":    "place",
    }
    kind = kind_map.get(ent_label, "entity")
    return EX[f"{kind}/{slugify(ent_text)}"]


def ner_label_to_class(ent_label: str):
    """
    Map a spaCy NER label to the corresponding Schema.org class URI.
    Example: 'PERSON' to schema:Person
    """
    mapping = {
        "PERSON": SCHEMA.Person,
        "ORG":    SCHEMA.Organization,
        "GPE":    SCHEMA.Place,
    }
    return mapping.get(ent_label, SCHEMA.Thing)


#Noise filtering 

def looks_like_noise(text: str) -> bool:
    """Apply heuristic rules to filter out entity texts that are likely noise or non-entities.
    Returns True if the text looks like noise and should be filtered out."""
    t = text.strip().lower()

    if not t:
        return True
    if len(t) < 3:
        return True
    if len(t) > 40:
        return True
    if len(t.split()) > 6:
        return True

    #filter wikipedia references
    if re.search(r'\[\d+\]', text):
        return True

    # filter weird punctuatuion patterns
    if re.search(r'\.\[|\]\.|^\d+\.\[', t):
        return True

    
    if t.startswith(("a ", "an ", "the ")):
        return True

    # filter geographical coordinates and measurements (e.g. "64.1833° N, 51.7214° W" or "2 million inhabitants")
    if re.search(r'^[øÅå°\d]', text):
        return True

    if any(x in t for x in BAD_ENTITY_SUBSTRINGS):
        return True
    if t in BAD_EXACT_ENTITIES:
        return True
    if re.search(r"[@/=:]", t):
        return True
    if t.startswith(("si ", "en el ", "lo que ")):
        return True
    if re.search(r'\d+\]\s*$', t):      # finit par [123]
        return True
    if re.search(r'["\(\,]$', t):       # finit par " ( ,
        return True  
    if re.search(r'^[a-z]{1,3}\s+[a-z]{1,3}$', t):  # "ab ac", "de la"
        return True
    if ',' in t and len(t.split()) <= 3:  # "Braun, Elisa"
        return True

    return False


def is_good_entity(text: str) -> bool:
    """Return True if the entity text passes all noise filters."""
    return not looks_like_noise(text)


# Baseline relation extraction 

def extract_sentence_relations(sent):
    """
    Baseline relation extraction from a spaCy sentence.
    If a sentence has >= 2 named entities, connect the first two
    using the ROOT verb lemma as the predicate.
    Returns a list of (subject_span, predicate_uri, object_span) tuples.
    """
    ents = [e for e in sent.ents if e.label_ in ("PERSON", "ORG", "GPE")]
    if len(ents) < 2:
        return []

    root = sent.root
    if root.pos_ != "VERB":
        return []

    subj = ents[0]
    obj  = ents[1]
    pred = EX[f"rel/{slugify(root.lemma_)}"]

    return [(subj, pred, obj)]