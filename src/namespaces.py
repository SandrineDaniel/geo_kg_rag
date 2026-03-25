"""
namespaces.py
=============
RDF namespace definitions shared across the pipeline.

Used by all src/ modules to avoid redefining namespaces locally.
"""

from rdflib import Namespace
from rdflib.namespace import RDF, RDFS, OWL, XSD

# Local KG namespace
EX = Namespace("http://example.org/kg/")

# Standard vocabularies
SCHEMA = Namespace("http://schema.org/")

# Wikidata namespaces
WD  = Namespace("http://www.wikidata.org/entity/")
WDT = Namespace("http://www.wikidata.org/prop/direct/")

# DBpedia (kept for reference)
DBR = Namespace("http://dbpedia.org/resource/")
DBO = Namespace("http://dbpedia.org/ontology/")