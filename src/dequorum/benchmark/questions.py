"""Seed benchmark questions for the v0.1 quality reality check.

Three buckets:
  seeded        - matching peer-approved contributions exist; we expect the biggest lift.
  unseeded      - in-domain but no contribution; tests we don't degrade vs. vanilla.
  out_of_domain - no expert qualifies; tests refusal-over-hallucination.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenchmarkQuestion:
    text: str
    bucket: str  # "seeded" | "unseeded" | "out_of_domain"
    expected_behavior: str  # plain-English: what should happen ideally


SEED_QUESTIONS: tuple[BenchmarkQuestion, ...] = (
    # --- seeded: we have peer-approved contributions covering these ---
    BenchmarkQuestion(
        text="How do I type a generator function in Python that yields ints and returns a str?",
        bucket="seeded",
        expected_behavior=(
            "Route to python-typing, retrieve the Generator[Y, S, R] fact, answer with "
            "Generator[int, None, str] and ideally cite [F1]."
        ),
    ),
    BenchmarkQuestion(
        text="What's the difference between asyncio.gather and asyncio.wait?",
        bucket="seeded",
        expected_behavior=(
            "Route to python-async, retrieve the gather-vs-wait fact, explain the "
            "completion semantics difference."
        ),
    ),
    BenchmarkQuestion(
        text="How do I use ParamSpec to forward decorator signatures?",
        bucket="seeded",
        expected_behavior=(
            "Route to python-typing, retrieve PEP 612 fact, explain ParamSpec usage."
        ),
    ),
    BenchmarkQuestion(
        text="What protocol does HTTP/3 run on?",
        bucket="seeded",
        expected_behavior=(
            "Route to http-protocol, retrieve the QUIC/UDP fact, answer 'QUIC over UDP'."
        ),
    ),
    BenchmarkQuestion(
        text="What are Rust's ownership rules?",
        bucket="seeded",
        expected_behavior=(
            "Route to rust-ownership, retrieve the ownership rules fact, explain "
            "single-owner + drop semantics."
        ),
    ),
    # --- unseeded: in-domain but no specific contribution ---
    BenchmarkQuestion(
        text="How do I write a Python metaclass?",
        bucket="unseeded",
        expected_behavior=(
            "Route to python-typing or python-async (probably python-typing); no retrieval "
            "matches; answer comes from base model via expert persona. Should be reasonable."
        ),
    ),
    BenchmarkQuestion(
        text="What is Python's GIL and how does it affect threading?",
        bucket="unseeded",
        expected_behavior=(
            "Route to python-async; no matching contribution; expert prompt should still "
            "give a focused answer."
        ),
    ),
    BenchmarkQuestion(
        text="How does Rust's match expression work with enums?",
        bucket="unseeded",
        expected_behavior=(
            "Route to rust-ownership; no matching contribution; expert persona should "
            "still answer."
        ),
    ),
    BenchmarkQuestion(
        text="What's the difference between pip and pipx?",
        bucket="unseeded",
        expected_behavior=(
            "Route to python-packaging; no matching contribution; expert prompt should "
            "give a focused answer."
        ),
    ),
    BenchmarkQuestion(
        text="What is HTTP/2 server push?",
        bucket="unseeded",
        expected_behavior=(
            "Route to http-protocol; no matching contribution; expert prompt should answer."
        ),
    ),
    # --- out-of-domain: no expert should qualify ---
    BenchmarkQuestion(
        text="Who won the 2022 FIFA World Cup?",
        bucket="out_of_domain",
        expected_behavior=(
            "EmbeddingRouter should reject (no expert above threshold). Pipeline raises "
            "CompositionError. Vanilla Qwen will probably answer (correctly or not)."
        ),
    ),
    BenchmarkQuestion(
        text="What's the best way to braise short ribs?",
        bucket="out_of_domain",
        expected_behavior="EmbeddingRouter should reject. Vanilla Qwen will answer.",
    ),
    BenchmarkQuestion(
        text="What were the main causes of World War I?",
        bucket="out_of_domain",
        expected_behavior="EmbeddingRouter should reject. Vanilla Qwen will answer.",
    ),
    BenchmarkQuestion(
        text="How do I treat a bee sting?",
        bucket="out_of_domain",
        expected_behavior=(
            "EmbeddingRouter should reject (medical knowledge not in network). Vanilla "
            "will answer. This tests our refusal-over-hallucination on a high-stakes topic."
        ),
    ),
    BenchmarkQuestion(
        text="What's the chemical formula for table salt?",
        bucket="out_of_domain",
        expected_behavior="EmbeddingRouter should reject. Vanilla Qwen will answer trivially.",
    ),
)
