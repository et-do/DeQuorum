"""Compose the three nodes into a single deterministic diagnose() call."""

from __future__ import annotations

from dequorum.category.composition import Morphism, compose
from dequorum.expert_network.nodes import ChemicalNode, LegalNode, PharmaNode

from dequorum.core.proof import ProofObject


def diagnose(symptom: str, age: int) -> ProofObject:
    return compose(
        {"symptom": symptom, "age": age},
        Morphism(ChemicalNode()),
        Morphism(PharmaNode()),
        Morphism(LegalNode()),
    )
