"""Invariant 2: every output carries a non-empty, signed provenance chain."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from ai_playground.core.errors import CompositionError
from ai_playground.expert_network.nodes import ChemicalNode
from ai_playground.expert_network.pipeline import diagnose

symptoms = st.sampled_from(sorted(ChemicalNode.DATA.keys()))
ages = st.integers(min_value=0, max_value=120)


@given(symptom=symptoms, age=ages)
def test_every_successful_output_has_provenance(symptom: str, age: int) -> None:
    try:
        proof = diagnose(symptom, age)
    except CompositionError:
        return
    assert len(proof.chain) > 0
    for sig in proof.chain:
        assert sig.node_id
        assert sig.digest
        assert sig.input_hash
        assert sig.output_hash


@given(symptom=symptoms, age=ages)
def test_chain_node_ids_match_pipeline_order(symptom: str, age: int) -> None:
    try:
        proof = diagnose(symptom, age)
    except CompositionError:
        return
    assert proof.node_ids == ("chemical", "pharma", "legal")
