"""End-to-end pipeline: route → retrieve → invoke experts → combine → credit."""

from __future__ import annotations

from dataclasses import dataclass

from ai_playground.base_model import BaseModel
from ai_playground.contributions import Contribution
from ai_playground.core.errors import CompositionError
from ai_playground.core.ledger import AttributionLedger
from ai_playground.core.node import Signature
from ai_playground.core.proof import ProofObject
from ai_playground.experts import Expert
from ai_playground.retrieval import Retriever, ScoredContribution
from ai_playground.router import KeywordRouter, RoutingResult


@dataclass(frozen=True, slots=True)
class ExpertAnswer:
    expert: Expert
    answer: str
    signature: Signature
    retrieved: tuple[ScoredContribution, ...]


@dataclass(frozen=True, slots=True)
class NetworkResponse:
    query: str
    routing: RoutingResult
    expert_answers: tuple[ExpertAnswer, ...]
    final_answer: str
    proof: ProofObject


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


def _combine_answers(answers: tuple[ExpertAnswer, ...]) -> str:
    if len(answers) == 1:
        return answers[0].answer
    sections = [
        f"### {a.expert.display_name} ({a.expert.expert_id})\n\n{a.answer}"
        for a in answers
    ]
    return "\n\n---\n\n".join(sections)


class Pipeline:
    """Wires routing, retrieval, expert invocation, attribution, and ledger credits."""

    def __init__(
        self,
        router: KeywordRouter,
        model: BaseModel,
        ledger: AttributionLedger | None = None,
        retriever: Retriever | None = None,
        *,
        top_k: int = 3,
        retrieve_top_k: int = 3,
    ) -> None:
        self._router = router
        self._model = model
        self._ledger = ledger or AttributionLedger()
        self._retriever = retriever
        self._top_k = top_k
        self._retrieve_top_k = retrieve_top_k

    @property
    def ledger(self) -> AttributionLedger:
        return self._ledger

    def query(self, q: str) -> NetworkResponse:
        if not q.strip():
            raise CompositionError("query must be non-empty")

        routing = self._router.route(q, top_k=self._top_k)
        if not routing.selected:
            raise CompositionError(
                "no experts available — register one or enable router fallback"
            )

        chain: list[Signature] = []
        answers: list[ExpertAnswer] = []
        for expert in routing.selected:
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
                )
            )

        final = _combine_answers(tuple(answers))
        proof = ProofObject(output=final, chain=tuple(chain))
        self._ledger.credit(proof)

        return NetworkResponse(
            query=q,
            routing=routing,
            expert_answers=tuple(answers),
            final_answer=final,
            proof=proof,
        )
