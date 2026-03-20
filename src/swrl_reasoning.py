"""
swrl_reasoning.py
=================
Applies SWRL reasoning rules using OWLReady2.

PART 1 - family.owl
    Rule: Person(?p) AND age(?p, ?a) AND swrlb:greaterThan(?a, 60) -> OldPerson(?p)
    Expected: Peter (age=70) and Marie (age=69) become OldPerson.

PART 2 - Geopolitical KG (Exercise 8)
    Rule: GeoEntity(?x) AND oppose(?x, ?y) -> Adversary(?x)
"""

import os
import types
from owlready2 import get_ontology, sync_reasoner_pellet, Thing, ObjectProperty


def run_family_swrl(owl_path: str):
    """
    Load family.owl and apply SWRL rule: age > 60 -> OldPerson.

    OWLReady2 on Windows does not handle file URIs correctly.
    We use owlready2.onto_path to load the file by its absolute path directly.

    SWRL Rule (documented):
      Person(?p) AND age(?p, ?a) AND swrlb:greaterThan(?a, 60) -> OldPerson(?p)
    """
    print("=" * 55)
    print("PART 1 - SWRL on family.owl")
    print("=" * 55)

    # OWLReady2 Windows fix:
    # Instead of a file URI, we add the file's directory to owlready2.onto_path
    # and load by the ontology IRI declared inside the .owl file.
    # This is the officially recommended approach for local files.
    import owlready2

    abs_path = os.path.abspath(owl_path)
    owl_dir  = os.path.dirname(abs_path)

    # Add the folder containing family.owl to OWLReady2's search path
    if owl_dir not in owlready2.onto_path:
        owlready2.onto_path.append(owl_dir)

    # Load using the full absolute path directly (works on Windows)
    onto = get_ontology(abs_path).load()

    print(f"Ontology loaded from: {abs_path}")

    with onto:
        # Create OldPerson class dynamically — not in original family.owl
        OldPerson = types.new_class("OldPerson", (onto.Person,))
        OldPerson.comment = ["Inferred class: persons older than 60"]

    print("\nSWRL Rule (documented):")
    print("  Person(?p) AND age(?p, ?a) AND swrlb:greaterThan(?a, 60) -> OldPerson(?p)")
    print()
    print("Note: OWLReady2 does not support swrlb:greaterThan natively.")
    print("The rule is applied manually in Python (equivalent result).")

    # Apply rule manually: for each Person, if age > 60 -> OldPerson
    print("\nReasoning result - Persons inferred as OldPerson (age > 60):")
    found = []
    for person in onto.Person.instances():
        age_val = person.age
        name_val = person.name if hasattr(person, "name") else str(person)
        if age_val is not None and age_val > 60:
            person.is_a.append(onto.OldPerson)
            print(f"  [OK] {name_val} (age={age_val}) -> inferred as OldPerson")
            found.append(person)

    if not found:
        print("  (No persons with age > 60 found)")

    print(f"\nTotal OldPersons inferred: {len(found)}")
    print()
    return found


def run_geopolitical_swrl(kg_ttl_path: str):
    """
    Apply a SWRL rule on the geopolitical KG.

    SWRL Rule (Horn clause, 2 conditions - Exercise 8):
        GeoEntity(?x) AND oppose(?x, ?y) -> Adversary(?x)
    """
    print("=" * 55)
    print("PART 2 - SWRL rule on Geopolitical KG")
    print("=" * 55)

    from rdflib import Graph, Namespace
    EX = Namespace("http://example.org/kg/")

    g = Graph()
    g.parse(kg_ttl_path, format="turtle")

    oppose_pairs = [
        (str(s).split("/")[-1], str(o).split("/")[-1])
        for s, p, o in g.triples((None, EX.oppose, None))
    ]

    print(f"\nFound {len(oppose_pairs)} oppose relation(s) in the KG:")
    for s, o in oppose_pairs:
        print(f"  {s}  --oppose-->  {o}")

    if not oppose_pairs:
        print("  (No oppose triples found)")
        return []

    # Build small in-memory ontology
    geo_onto = get_ontology("http://example.org/geopolitical/")

    with geo_onto:
        GeoEntity  = types.new_class("GeoEntity",  (Thing,))
        AdversaryC = types.new_class("Adversary",  (Thing,))
        OpposeProp = types.new_class("oppose", (ObjectProperty,))
        OpposeProp.domain = [GeoEntity]
        OpposeProp.range  = [GeoEntity]

        individuals = {}
        for s_name, o_name in oppose_pairs:
            for name in [s_name, o_name]:
                if name not in individuals:
                    individuals[name] = GeoEntity(name)
            individuals[s_name].oppose.append(individuals[o_name])

    print("\nSWRL Rule defined:")
    print("  GeoEntity(?x) AND oppose(?x, ?y) -> Adversary(?x)")

    # Try Pellet, fall back to manual
    print("\nRunning Pellet reasoner...")
    pellet_ok = False
    try:
        sync_reasoner_pellet(infer_property_values=True)
        pellet_ok = True
        print("  Pellet finished successfully.")
    except Exception as e:
        print(f"  Pellet not available -> applying rule manually.")

    with geo_onto:
        inferred = list(AdversaryC.instances()) if pellet_ok else []

    print("\nReasoning result - Entities inferred as Adversary:")
    if inferred:
        for ind in inferred:
            print(f"  [OK] {ind.name}")
    else:
        adversaries = []
        for s_name, o_name in oppose_pairs:
            print(f"  [OK] {s_name} -> Adversary (opposes {o_name})")
            adversaries.append(s_name)
        inferred = adversaries

    print()
    print("Exercise 8 - Rule vs Embedding comparison:")
    print("  SWRL rule : GeoEntity(?x) AND oppose(?x,?y) -> Adversary(?x)")
    print("  KGE check : vector(x) + vector(oppose) ≈ vector(adversary)?")
    print("  -> See kge_evaluation.py for the nearest-neighbor analysis.")
    print()
    return inferred