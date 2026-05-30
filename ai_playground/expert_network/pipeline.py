"""Compose the three nodes into a single deterministic diagnose() call."""

from __future__ import annotations

from ai_playground.category.composition import Morphism, compose
from ai_playground.core.proof import ProofObject
from ai_playground.expert_network.nodes import ChemicalNode, LegalNode, PharmaNode


def diagnose(symptom: str, age: int) -> ProofObject:
    return compose(
        {"symptom": symptom, "age": age},
        Morphism(ChemicalNode()),
        Morphism(PharmaNode()),
        Morphism(LegalNode()),
    )
