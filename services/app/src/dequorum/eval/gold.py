"""Gold key facts for the seeded benchmark queries.

Each entry is the set of correct, load-bearing facts a good answer must
contain — derived from the peer-approved contributions that ground these
queries. Used by KeywordRecallJudge as an independent quality signal. Keyed
by the exact question text in benchmark/questions.py (a test asserts every
seeded question has an entry, so drift is caught).
"""

from __future__ import annotations

from dataclasses import dataclass

SEEDED_GOLD: dict[str, tuple[str, ...]] = {
    "How do I type a generator function in Python that yields ints and "
    "returns a str?": ("Generator", "int", "None", "str"),
    "What's the difference between asyncio.gather and asyncio.wait?": (
        "gather",
        "wait",
        "results",
        "pending",
    ),
    "How do I use ParamSpec to forward decorator signatures?": (
        "ParamSpec",
        "Callable",
    ),
    "What protocol does HTTP/3 run on?": ("QUIC", "UDP"),
    "What are Rust's ownership rules?": ("owner", "borrow", "scope"),
}

# Paraphrase variants that route to the same categories and retrieve the same
# contributions, with the same gold facts. They multiply the (query, fact)
# pairs available to the faithfulness study (§8.6) without changing the corpus
# — each variant is an additional, independent test of the same knowledge.
GOLD_VARIANTS: dict[str, tuple[str, ...]] = {
    "How do I annotate a Python generator that yields ints and returns a str?": (
        "Generator",
        "int",
        "None",
        "str",
    ),
    "What's the correct type hint for a generator function that returns a string?": (
        "Generator",
        "int",
        "None",
        "str",
    ),
    "How should I type a generator's yield and return values in Python?": (
        "Generator",
        "int",
        "None",
        "str",
    ),
    "When should I use asyncio.gather instead of asyncio.wait?": (
        "gather",
        "wait",
        "results",
        "pending",
    ),
    "How do asyncio.gather and asyncio.wait differ in handling results?": (
        "gather",
        "wait",
        "results",
        "pending",
    ),
    "What is the completion-semantics difference between gather and wait in asyncio?": (
        "gather",
        "wait",
        "results",
        "pending",
    ),
    "How do I preserve a decorator's signature using ParamSpec?": (
        "ParamSpec",
        "Callable",
    ),
    "What is ParamSpec used for in Python typing?": ("ParamSpec", "Callable"),
    "How does PEP 612 ParamSpec help type a decorator's Callable?": (
        "ParamSpec",
        "Callable",
    ),
    "Which transport protocol underlies HTTP/3?": ("QUIC", "UDP"),
    "Does HTTP/3 use QUIC, and what does QUIC run on?": ("QUIC", "UDP"),
    "What is the transport layer for HTTP/3?": ("QUIC", "UDP"),
    "What are the core ownership rules in Rust?": ("owner", "borrow", "scope"),
    "How does Rust enforce memory safety through ownership?": (
        "owner",
        "borrow",
        "scope",
    ),
    "Explain Rust's borrowing and ownership model.": (
        "owner",
        "borrow",
        "scope",
    ),
}


def gold_for(query: str) -> tuple[str, ...]:
    """Gold key facts for a query (canonical or variant), or () if none."""
    return SEEDED_GOLD.get(query) or GOLD_VARIANTS.get(query, ())


@dataclass(frozen=True, slots=True)
class GoldQuestion:
    """A gold-annotated query. Duck-types the BenchmarkQuestion fields the
    attribution harness reads (`text`, `bucket`), without importing the
    benchmark package (which would be a cycle)."""

    text: str
    bucket: str = "seeded"


def gold_questions() -> list[GoldQuestion]:
    """All gold-annotated queries (canonical + variants) for the faithfulness
    study — the larger sample §8.6/§8.8 calls for."""
    return [GoldQuestion(text=q) for q in (*SEEDED_GOLD, *GOLD_VARIANTS)]
