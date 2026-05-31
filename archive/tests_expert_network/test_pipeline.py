from __future__ import annotations

import pytest
from dequorum.expert_network.pipeline import diagnose

from dequorum.core.errors import MissingData
from dequorum.core.ledger import AttributionLedger


def test_end_to_end_approved_case() -> None:
    proof = diagnose("fatigue", age=20)
    assert proof.output["drug"] == "ferrous_sulfate"
    assert proof.output["approved"] is True
    assert proof.node_ids == ("chemical", "pharma", "legal")


def test_end_to_end_denied_case() -> None:
    proof = diagnose("muscle_cramps", age=10)
    assert proof.output["drug"] == "potassium_chloride"
    assert proof.output["approved"] is False
    assert proof.output["min_age"] == 18


def test_ledger_credits_one_token_per_node() -> None:
    proof = diagnose("headache", age=18)
    ledger = AttributionLedger()
    ledger.credit(proof)
    assert ledger.totals() == {"chemical": 1, "pharma": 1, "legal": 1}


def test_unknown_symptom_raises() -> None:
    with pytest.raises(MissingData):
        diagnose("hangnail", age=30)
