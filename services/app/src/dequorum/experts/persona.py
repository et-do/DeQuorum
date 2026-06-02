"""Experts: signed personas that contribute knowledge to the network."""

from __future__ import annotations

from dataclasses import dataclass

from dequorum.core.hashing import canonical_bytes, digest
from dequorum.core.node import Signature


@dataclass(frozen=True, slots=True)
class Expert:
    """A signed expert persona: who they are + how they answer.

    `example_questions` are NOT part of the persona's behavior contract
    (so they don't affect `prompt_digest`); they exist to enrich the text
    the embedding router sees when matching queries to experts.
    """

    expert_id: str
    display_name: str
    specialty_tags: tuple[str, ...]
    system_prompt: str
    signing_key: bytes
    example_questions: tuple[str, ...] = ()

    @property
    def prompt_digest(self) -> str:
        return digest(canonical_bytes(self.system_prompt))

    def sign_answer(self, query: str, answer: str) -> Signature:
        return Signature.sign(
            node_id=self.expert_id,
            signing_key=self.signing_key,
            payload={"query": query, "prompt_digest": self.prompt_digest},
            result=answer,
        )


class ExpertRegistry:
    """In-memory registry of experts, addressable by id and tag."""

    def __init__(self) -> None:
        self._experts: dict[str, Expert] = {}

    def register(self, expert: Expert) -> None:
        if expert.expert_id in self._experts:
            raise ValueError(f"expert_id already registered: {expert.expert_id!r}")
        self._experts[expert.expert_id] = expert

    def get(self, expert_id: str) -> Expert:
        if expert_id not in self._experts:
            raise KeyError(f"unknown expert_id: {expert_id!r}")
        return self._experts[expert_id]

    def all(self) -> tuple[Expert, ...]:
        return tuple(self._experts.values())

    def by_tag(self, tag: str) -> tuple[Expert, ...]:
        tag_lower = tag.lower()
        return tuple(
            e
            for e in self._experts.values()
            if any(t.lower() == tag_lower for t in e.specialty_tags)
        )

    def __len__(self) -> int:
        return len(self._experts)

    def __contains__(self, expert_id: object) -> bool:
        return isinstance(expert_id, str) and expert_id in self._experts
