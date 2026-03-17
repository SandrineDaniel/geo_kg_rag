from rdflib import Namespace
from rdflib.namespace import RDF, RDFS, OWL, XSD
# Define namespaces for the knowledge graph to not call them in the code every time


EX = Namespace("http://example.org/kg/")
SCHEMA = Namespace("http://schema.org/")
DBR = Namespace("http://dbpedia.org/resource/")
DBO = Namespace("http://dbpedia.org/ontology/")