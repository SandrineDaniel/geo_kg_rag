import re
from rdflib import URIRef
from src.namespaces import EX, SCHEMA
import re
import unicodedata
from rdflib import URIRef
from src.namespaces import EX, SCHEMA


BAD_ENTITY_SUBSTRINGS = {
    "cuenta", "contraseña", "premium", "suscripción", "cookies",
    "usuario", "dispositivo", "lectura", "términos", "condiciones",
    "compartir", "compartiendo", "contratar", "personalizar",
    "aquí", "aqui", "podrás", "podras", "mensaje", "vuestra experiencia",
    "el país usa edition", "usa edition"
}

BAD_EXACT_ENTITIES = {
    "cada", "davos", "militarily", "defence", "government",
    "house", "forum", "frontpage"
}
BAD_EXACT_ENTITIES.update({
    "cambia tu", "demark", "leyen", "nielsen", "mette",
    "farage", "frederiksen", "miller", "ciobanu", "rostrup"
})

PERSON_HINTS = {
    "trump", "macron", "putin", "frederiksen", "rutte", "zelenskiy",
    "biden", "rubio", "vance", "milei", "meloni", "merz"
}

ORG_HINTS = {
    "nato", "government", "ministry", "department", "house",
    "institute", "university", "commission", "force", "post",
    "times", "guardian", "cnn", "pentagon"
}


def correct_entity_label(text: str, predicted_label: str) -> str:
    t = text.strip().lower()

    # personnes connues
    if any(name in t for name in PERSON_HINTS):
        return "PERSON"

    # organisations probables
    if any(word in t for word in ORG_HINTS):
        return "ORG"

    # lieux fréquents de ton corpus
    if t in {
        "greenland", "denmark", "washington", "nuuk", "copenhagen",
        "russia", "china", "ukraine", "alaska", "iceland", "norway",
        "the united states", "u.s.", "usa"
    }:
        return "GPE"

    return predicted_label

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def make_entity_uri(ent_text: str, ent_label: str) -> URIRef:
    kind_map = {
        "PERSON": "person",
        "ORG": "org",
        "GPE": "place",
    }
    kind = kind_map.get(ent_label, "entity")
    return EX[f"{kind}/{slugify(ent_text)}"]


def ner_label_to_class(ent_label: str):
    if ent_label == "PERSON":
        return SCHEMA.Person
    if ent_label == "ORG":
        return SCHEMA.Organization
    if ent_label == "GPE":
        return SCHEMA.Place
    return SCHEMA.Thing


def looks_like_noise(text: str) -> bool:
    t = text.strip().lower()

    if not t:
        return True

    if len(t) < 3:
        return True

    if len(t) > 40:
        return True

    if len(t.split()) > 6:
        return True

    if any(x in t for x in BAD_ENTITY_SUBSTRINGS):
        return True

    if t in BAD_EXACT_ENTITIES:
        return True

    # trop de ponctuation / fragments bizarres
    if re.search(r"[@/=:]", t):
        return True

    # commence par verbe/article bizarre fréquent dans le bruit
    if t.startswith(("si ", "en el ", "lo que ", "permitira ", "recomendamos ")):
        return True

    return False


def is_good_entity(text: str) -> bool:
    return not looks_like_noise(text)

def extract_sentence_relations(sent):
    """
    Baseline relation extraction:
    If a sentence has >=2 named entities, connect the first 2 using the ROOT verb lemma.
    """
    ents = [e for e in sent.ents if e.label_ in ("PERSON", "ORG", "GPE")]
    if len(ents) < 2:
        return []

    root = sent.root
    if root.pos_ != "VERB":
        return []

    subj = ents[0]
    obj = ents[1]

    pred = EX[f"rel/{slugify(root.lemma_)}"]
    return [(subj, pred, obj)]

