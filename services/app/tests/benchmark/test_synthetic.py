from __future__ import annotations

from dequorum.benchmark.novelty import NoveltyFact
from dequorum.benchmark.synthetic import generate_facts


def test_generates_n_well_formed_distinct_facts() -> None:
    facts = generate_facts(50, seed=0)
    assert len(facts) == 50
    assert all(isinstance(f, NoveltyFact) for f in facts)
    # Every fact is usable by the existing benches: gold, paraphrase, false variant.
    for f in facts:
        assert f.gold and f.gold[0]
        assert f.query and f.note and f.paraphrase
        assert f.false_note and f.false_gold
        assert f.false_gold[0] != f.gold[0]  # the lie flips the value
        assert f.gold[0] not in f.paraphrase  # paraphrase is a question, not the answer
    # Gold tokens are distinct, so credit/recall don't collide across facts.
    assert len({f.gold[0] for f in facts}) == 50


def test_is_deterministic_by_seed() -> None:
    assert generate_facts(20, seed=3) == generate_facts(20, seed=3)
    assert generate_facts(20, seed=3) != generate_facts(20, seed=4)


def test_topics_below_n_forces_shared_systems() -> None:
    """With fewer topics than facts, facts reuse system names — the near-duplicate
    case for retrieval ranking and routing. With topics == n, all are distinct."""
    distinct = generate_facts(8, seed=0, topics=8)
    clustered = generate_facts(8, seed=0, topics=2)
    # crude proxy: clustered notes share more leading-word repeats than distinct
    lead_distinct = len({n.note.split()[1] for n in distinct})
    lead_clustered = len({n.note.split()[1] for n in clustered})
    assert lead_clustered <= lead_distinct


def test_rejects_nonpositive_n() -> None:
    import pytest

    with pytest.raises(ValueError):
        generate_facts(0)
