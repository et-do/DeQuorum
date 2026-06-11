"""Deterministic generator for invented-fact corpora at scale.

The hand-written corpus in `novelty.py` has eight facts — enough to demonstrate
a mechanism, too few to estimate anything. This module generates an arbitrary
number of facts of the same shape (`NoveltyFact`), built from pseudo-random
invented tokens so a pretrained model still cannot answer them without the note.
Everything is seeded, so a corpus is reproducible from `(n, seed)`.

Each fact carries a distinctive invented gold token (base recall ≈ 0, grounded
recall ≈ 1), a plausible-but-false variant with a *different* invented value
(for falsehood/conflict/judge studies), and a lexically-distinct paraphrase of
the query (for the memorization control). Four template families give the
distractor diversity that retrieval and routing benches need; the optional
`topics` argument forces near-duplicate facts that share a system name, the
hard case for retrieval ranking and routing-based attribution.
"""

from __future__ import annotations

from random import Random

from dequorum.benchmark.novelty import NoveltyFact

_CONS = "bdfgklmnprstvz"
_VOWEL = "aeiou"


def _word(rng: Random, syllables: int = 2) -> str:
    """A capitalized invented pseudo-word, e.g. 'Bavuko'."""
    syl = "".join(rng.choice(_CONS) + rng.choice(_VOWEL) for _ in range(syllables))
    return syl.capitalize()


def _value(rng: Random) -> str:
    """A distinctive invented value token, e.g. 'Zarn-7'."""
    return f"{_word(rng)}-{rng.randint(2, 97)}"


def _config_fact(rng: Random, system: str) -> NoveltyFact:
    param = f"{_word(rng).lower()}.{_word(rng).lower()}"
    val, false_val = _value(rng), _value(rng)
    return NoveltyFact(
        note=f"In the {system} planner, {param} defaults to {val}.",
        query=f"What is the default value of {param} in the {system} planner?",
        gold=(val,),
        paraphrase=f"In {system}, what does {param} resolve to when left unset?",
        false_note=f"In the {system} planner, {param} defaults to {false_val}.",
        false_gold=(false_val,),
    )


def _transport_fact(rng: Random, system: str) -> NoveltyFact:
    trans, false_trans = _word(rng), _word(rng)
    return NoveltyFact(
        note=f"The {system} protocol runs its handshake over {trans}.",
        query=f"What does the {system} protocol run its handshake over?",
        gold=(trans,),
        paraphrase=f"Which transport carries the {system} handshake?",
        false_note=f"The {system} protocol runs its handshake over {false_trans}.",
        false_gold=(false_trans,),
    )


def _bio_fact(rng: Random, system: str) -> NoveltyFact:
    cell = f"{system.lower()}cytes"
    sub, false_sub = _word(rng), _word(rng)
    gland = _word(rng)
    return NoveltyFact(
        note=f"{cell.capitalize()} secrete {sub} in the {gland} gland.",
        query=f"What do {cell} secrete, and in which gland?",
        gold=(sub, gland),
        paraphrase=f"Which substance do {cell} release, and where is it produced?",
        false_note=f"{cell.capitalize()} secrete {false_sub} in the {gland} gland.",
        false_gold=(false_sub, gland),
    )


def _threshold_fact(rng: Random, system: str) -> NoveltyFact:
    field = f"{_word(rng).lower()}.{_word(rng).lower()}"
    the = f"0.{rng.randint(2, 9)}"
    behavior, false_behavior = _word(rng), _word(rng)
    return NoveltyFact(
        note=f"When {field} exceeds {the} in {system}, the system enters {behavior}.",
        query=f"What happens when {field} exceeds {the} in {system}?",
        gold=(behavior,),
        paraphrase=f"In {system}, what state is triggered once {field} passes {the}?",
        false_note=(
            f"When {field} exceeds {the} in {system}, the system enters "
            f"{false_behavior}."
        ),
        false_gold=(false_behavior,),
    )


_TEMPLATES = (_config_fact, _transport_fact, _bio_fact, _threshold_fact)


def generate_facts(
    n: int, seed: int = 0, topics: int | None = None
) -> tuple[NoveltyFact, ...]:
    """Generate `n` invented facts, reproducibly from `seed`.

    `topics` controls how many distinct system names are drawn: with the default
    (`topics = n`) every fact is about a different system; setting `topics < n`
    forces near-duplicate facts that share a system name (lexically similar notes
    about the same entity) — the hard case for retrieval ranking and routing.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    rng = Random(seed)
    n_topics = n if topics is None else max(1, topics)
    # A stable pool of distinct system names; facts cycle through them so that
    # topics < n produces collisions (near-duplicate facts on the same system).
    systems: list[str] = []
    seen: set[str] = set()
    while len(systems) < n_topics:
        w = _word(rng, syllables=rng.choice((2, 3)))
        if w not in seen:
            seen.add(w)
            systems.append(w)
    facts: list[NoveltyFact] = []
    used_gold: set[str] = set()
    for i in range(n):
        system = systems[i % n_topics]
        template = _TEMPLATES[i % len(_TEMPLATES)]
        # Regenerate on the rare gold-token collision so every fact is distinct.
        for _ in range(8):
            fact = template(rng, system)
            if fact.gold[0] not in used_gold:
                break
        used_gold.add(fact.gold[0])
        facts.append(fact)
    return tuple(facts)
