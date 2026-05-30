"""End-to-end toy: 3 institutional nodes composed via categorical morphisms."""

from ai_playground.expert_network.nodes import (
    ChemicalNode,
    LegalNode,
    PharmaNode,
)
from ai_playground.expert_network.pipeline import diagnose

__all__ = ["ChemicalNode", "LegalNode", "PharmaNode", "diagnose"]
