"""End-to-end pipeline: route → retrieve → invoke experts → compose → credit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dequorum.base_model import BaseModel
from dequorum.composition import (
    CompositionResult,
    CompositionStrategy,
    PickBestStrategy,
)
from dequorum.contributions import Contribution
from dequorum.core.errors import CompositionError
from dequorum.core.ledger import AttributionLedger
from dequorum.core.node import Signature
from dequorum.core.proof import ProofObject
from dequorum.experts import Expert
from dequorum.retrieval import Retriever, ScoredContribution
from dequorum.router import RoutingResult


class Router(Protocol):
    method: str

    def route(self, query: str, top_k: int = 3) -> RoutingResult: ...


@dataclass(frozen=True, slots=True)
class ExpertAnswer:
    expert: Expert
    answer: str
    signature: Signature
    retrieved: tuple[ScoredContribution, ...]
    routing_score: float


@dataclass(frozen=True, slots=True)
class NetworkResponse:
    query: str
    routing: RoutingResult
    expert_answers: tuple[ExpertAnswer, ...]
    composition: CompositionResult
    proof: ProofObject

    @property
    def final_answer(self) -> str:
        return self.composition.text


def _augment_system_prompt(
    base_prompt: str, contributions: tuple[Contribution, ...]
) -> str:
    if not contributions:
        return base_prompt
    lines = [
        base_prompt,
        "",
        "Use only the following verified facts contributed by the network. "
        "Each is labeled [F#] — cite the label when you use the fact. "
        "If a question is not answerable from these facts, say so explicitly.",
        "",
    ]
    for i, c in enumerate(contributions, start=1):
        cite = f"  (sources: {', '.join(c.citations)})" if c.citations else ""
        lines.append(f"[F{i}] {c.text}{cite}")
    return "\n".join(lines)


class Pipeline:
    """Wires routing, retrieval, expert invocation, attribution, and ledger credits."""

    def __init__(
        self,
        router: Router,
        model: BaseModel,
        ledger: AttributionLedger | None = None,
        retriever: Retriever | None = None,
        composition: CompositionStrategy | None = None,
        *,
        top_k: int = 3,
        retrieve_top_k: int = 3,
    ) -> None:
        self._router = router
        self._model = model
        self._ledger = ledger or AttributionLedger()
        self._retriever = retriever
        self._composition = composition or PickBestStrategy()
        self._top_k = top_k
        self._retrieve_top_k = retrieve_top_k

    @property
    def ledger(self) -> AttributionLedger:
        return self._ledger

    @property
    def composition(self) -> CompositionStrategy:
        return self._composition

    def query(self, q: str) -> NetworkResponse:
        if not q.strip():
            raise CompositionError("query must be non-empty")

        routing = self._router.route(q, top_k=self._top_k)
        if not routing.selected:
            raise CompositionError(
                "no qualified expert above the routing threshold "
                "— register a relevant expert or lower the threshold"
            )

        chain: list[Signature] = []
        answers: list[ExpertAnswer] = []
        for sel in routing.selected:
            expert = sel.expert
            retrieved: tuple[ScoredContribution, ...] = ()
            if self._retriever is not None:
                retrieved = tuple(
                    self._retriever.retrieve(
                        q, expert.expert_id, top_k=self._retrieve_top_k
                    )
                )

            aug_prompt = _augment_system_prompt(
                expert.system_prompt, tuple(sc.contribution for sc in retrieved)
            )
            text = self._model.complete(system=aug_prompt, user=q)
            expert_sig = expert.sign_answer(query=q, answer=text)

            for sc in retrieved:
                chain.append(sc.contribution.signature)
            chain.append(expert_sig)

            answers.append(
                ExpertAnswer(
                    expert=expert,
                    answer=text,
                    signature=expert_sig,
                    retrieved=retrieved,
                    routing_score=sel.score,
                )
            )

        composition_result = self._composition.compose(tuple(answers))
        proof = ProofObject(output=composition_result.text, chain=tuple(chain))
        self._ledger.credit(proof)

        return NetworkResponse(
            query=q,
            routing=routing,
            expert_answers=tuple(answers),
            composition=composition_result,
            proof=proof,
        )
