"""Invariant 1: same input always yields byte-identical output."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from dequorum.core.errors import CompositionError
from dequorum.expert_network.nodes import ChemicalNode
from dequorum.expert_network.pipeline import diagnose

symptoms = st.sampled_from([*sorted(ChemicalNode.DATA.keys()), "__unknown__"])
ages = st.integers(min_value=0, max_value=120)


@given(symptom=symptoms, age=ages)
def test_diagnose_is_byte_identical_across_runs(symptom: str, age: int) -> None:
    try:
        p1 = diagnose(symptom, age)
        p2 = diagnose(symptom, age)
    except CompositionError:
        return
    assert p1.chain == p2.chain
    assert p1.output == p2.output


@given(symptom=symptoms, age=ages)
def test_failure_is_reproducible(symptom: str, age: int) -> None:
    try:
        diagnose(symptom, age)
    except CompositionError as first:
        try:
            diagnose(symptom, age)
        except CompositionError as second:
            assert type(first) is type(second)
            assert str(first) == str(second)
            return
        raise AssertionError("second call did not raise")
