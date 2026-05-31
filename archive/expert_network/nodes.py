"""Three sample institutional nodes operating over a shared context dict."""

from __future__ import annotations

from typing import Any, ClassVar

from dequorum.core.errors import MissingData
from dequorum.core.node import Node

Context = dict[str, Any]


class ChemicalNode(Node):
    """Symptoms → chemical deficiency."""

    DATA: ClassVar[dict[str, str]] = {
        "fatigue": "iron_deficiency",
        "headache": "magnesium_deficiency",
        "muscle_cramps": "potassium_deficiency",
    }

    def __init__(self) -> None:
        super().__init__(node_id="chemical", signing_key=b"chemical-node-key")

    def _answer(self, payload: Context) -> Context:
        symptom = payload["symptom"]
        if symptom not in self.DATA:
            raise MissingData(f"chemical: no entry for symptom {symptom!r}")
        return {**payload, "deficiency": self.DATA[symptom]}


class PharmaNode(Node):
    """Deficiency → approved drug name."""

    DATA: ClassVar[dict[str, str]] = {
        "iron_deficiency": "ferrous_sulfate",
        "magnesium_deficiency": "magnesium_citrate",
        "potassium_deficiency": "potassium_chloride",
    }

    def __init__(self) -> None:
        super().__init__(node_id="pharma", signing_key=b"pharma-node-key")

    def _answer(self, payload: Context) -> Context:
        deficiency = payload["deficiency"]
        if deficiency not in self.DATA:
            raise MissingData(f"pharma: no drug for {deficiency!r}")
        return {**payload, "drug": self.DATA[deficiency]}


class LegalNode(Node):
    """Drug + patient age → prescribing verdict."""

    MIN_AGE: ClassVar[dict[str, int]] = {
        "ferrous_sulfate": 12,
        "magnesium_citrate": 16,
        "potassium_chloride": 18,
    }

    def __init__(self) -> None:
        super().__init__(node_id="legal", signing_key=b"legal-node-key")

    def _answer(self, payload: Context) -> Context:
        drug = payload["drug"]
        age = payload["age"]
        if drug not in self.MIN_AGE:
            raise MissingData(f"legal: no rule for drug {drug!r}")
        min_age = self.MIN_AGE[drug]
        return {
            **payload,
            "min_age": min_age,
            "approved": age >= min_age,
        }
