"""Distillation proof-of-concept: turn the contribution corpus into model
weights (LoRA) and show attribution survives the distillation.

The whitepaper's long-term thesis (§3.5) is that the network's knowledge
stops being a retrieval-time augmentation and becomes the model. This
module is the toy-scale demonstration: train a LoRA on the seed
contributions, then check (a) the model recalls grounded facts *without*
retrieval, and (b) leaving one contributor's examples out removes exactly
their facts — i.e. the contributor→weight lineage is traceable. Heavy ML
imports (transformers/peft/torch) are lazy so the rest of the app and the
pure helpers stay importable without them.
"""

from __future__ import annotations

from dequorum.distill.poc import (
    TrainingExample,
    attribution_delta,
    build_examples,
    exclude_contributor,
)

__all__ = [
    "TrainingExample",
    "attribution_delta",
    "build_examples",
    "exclude_contributor",
]
