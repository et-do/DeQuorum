from __future__ import annotations

from dequorum.core.ledger import AttributionLedger
from dequorum.core.node import Signature
from dequorum.core.proof import ProofObject


def _sig(node_id: str) -> Signature:
    return Signature.sign(node_id=node_id, signing_key=b"k", payload=0, result=0)


def test_record_accumulates() -> None:
    ledger = AttributionLedger()
    ledger.record("a", 3)
    ledger.record("a", 2)
    ledger.record("b", 1)
    assert ledger.totals() == {"a": 5, "b": 1}


def test_credit_from_proof() -> None:
    proof = ProofObject(output=None, chain=(_sig("a"), _sig("b"), _sig("a")))
    ledger = AttributionLedger()
    ledger.credit(proof)
    assert ledger.totals() == {"a": 2, "b": 1}


def test_credit_scales_tokens_per_step() -> None:
    proof = ProofObject(output=None, chain=(_sig("a"), _sig("b")))
    ledger = AttributionLedger()
    ledger.credit(proof, tokens_per_step=5)
    assert ledger.totals() == {"a": 5, "b": 5}
