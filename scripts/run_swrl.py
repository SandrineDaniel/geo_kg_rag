"""
run_swrl.py
===========
Script to run SWRL reasoning for both exercises.
 
Run with:
    python scripts/run_swrl.py
 
Requirements:
    pip install owlready2
 
Note: Pellet reasoner requires Java to be installed on your machine.
If Java is not available, the script falls back to manual inference.
"""
 
import sys
import os
 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
 
from src.swrl_reasoning import run_family_swrl, run_geopolitical_swrl
 
if __name__ == "__main__":
 
    # ── PART 1: family.owl (required lab exercise) ───────────────────────────
    # Rule: Person(?p) ∧ age(?p, ?a) ∧ swrlb:greaterThan(?a, 60) → OldPerson(?p)
    # Expected: Peter (age=70) and Marie (age=69) become OldPerson
    run_family_swrl(
        owl_path="data/family.owl"
    )
 
    # ── PART 2: Geopolitical KG (Exercise 8) ─────────────────────────────────
    # Rule: GeoEntity(?x) ∧ oppose(?x, ?y) → Adversary(?x)
    # Uses the initial KG (step 1) which contains our extracted oppose relations
    run_geopolitical_swrl(
        kg_ttl_path="outputs/graphs/mykg_step1_initial.ttl"
    )
 