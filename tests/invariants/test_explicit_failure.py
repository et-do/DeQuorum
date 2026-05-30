"""Invariant 3: missing data halts explicitly; no fabricated answers."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ai_playground.core.errors import CompositionError, MissingData
from ai_playground.expert_network.nodes import ChemicalNode
from ai_playground.expert_network.pipeline import diagnose
from ai_playground.graph.routing import KnowledgeGraph

known_symptoms = set(ChemicalNode.DATA.keys())
arbitrary_symptoms = st.text(min_size=1, max_size=24).filter(
    lambda s: s not in known_symptoms
)
ages = st.integers(min_value=0, max_value=120)


@given(symptom=arbitrary_symptoms, age=ages)
def test_unknown_symptom_always_raises(symptom: str, age: int) -> None:
    with pytest.raises(MissingData):
        diagnose(symptom, age)


def test_graph_missing_path_raises_composition_error() -> None:
    g = KnowledgeGraph()
    g.add_fact("a", "rel", "b", source_node_id="s", signing_key=b"k")
    with pytest.raises(CompositionError):
        g.route("a", "z")
