"""Inference: base model adapter + composition strategies + the query pipeline."""

from dequorum.inference.base_model import BaseModel, MockBaseModel, OllamaBaseModel
from dequorum.inference.composition import (
    STRATEGIES,
    CompositionResult,
    CompositionStrategy,
    ConcatStrategy,
    PickBestStrategy,
    make_strategy,
)
from dequorum.inference.pipeline import (
    ExpertAnswer,
    NetworkResponse,
    Pipeline,
)

__all__ = [
    "STRATEGIES",
    "BaseModel",
    "CompositionResult",
    "CompositionStrategy",
    "ConcatStrategy",
    "ExpertAnswer",
    "MockBaseModel",
    "NetworkResponse",
    "OllamaBaseModel",
    "PickBestStrategy",
    "Pipeline",
    "make_strategy",
]
