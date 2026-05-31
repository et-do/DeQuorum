"""End-to-end toy: 3 institutional nodes composed via categorical morphisms."""

from dequorum.expert_network.nodes import (
    ChemicalNode,
    LegalNode,
    PharmaNode,
)
from dequorum.expert_network.pipeline import diagnose

__all__ = ["ChemicalNode", "LegalNode", "PharmaNode", "diagnose"]
