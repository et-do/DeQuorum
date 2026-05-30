"""Morphisms as Node calls; composition emits a strict ProofObject."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_playground.core.node import Node, Signature
from ai_playground.core.proof import ProofObject


@dataclass(frozen=True, slots=True)
class Morphism:
    node: Node

    def apply(self, payload: Any) -> tuple[Any, Signature]:
        result = self.node.query(payload)
        return result.value, result.signature


def compose(payload: Any, *morphisms: Morphism) -> ProofObject:
    if not morphisms:
        raise ValueError("compose requires at least one morphism")
    chain = []
    current = payload
    for morph in morphisms:
        current, sig = morph.apply(current)
        chain.append(sig)
    return ProofObject(output=current, chain=tuple(chain))
