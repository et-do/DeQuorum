from __future__ import annotations

from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.store import ContributionStore


def _c(expert: str, text: str) -> Contribution:
    return Contribution.create(
        expert_id=expert,
        contributor_id=expert,
        text=text,
        citations=("https://example.com",),
        signing_key=expert.encode(),
    )


def test_add_and_get() -> None:
    with ContributionStore() as s:
        c = _c("py", "hello")
        s.add(c)
        roundtrip = s.get(c.contribution_id)
        assert roundtrip == c


def test_idempotent_add() -> None:
    with ContributionStore() as s:
        c = _c("py", "hello")
        s.add(c)
        s.add(c)
        assert len(s) == 1


def test_list_for_expert_filters_correctly() -> None:
    with ContributionStore() as s:
        s.add(_c("py", "python fact"))
        s.add(_c("rs", "rust fact"))
        s.add(_c("py", "another python fact"))
        py = s.list_for_expert("py")
        assert len(py) == 2
        assert all(c.expert_id == "py" for c in py)


def test_iter_all() -> None:
    with ContributionStore() as s:
        s.add(_c("a", "1"))
        s.add(_c("b", "2"))
        assert {c.contribution_id for c in s} == {
            _c("a", "1").contribution_id,
            _c("b", "2").contribution_id,
        }


def test_persistence_across_store_instances() -> None:
    # Two stores backed by the same Postgres database see each other's writes.
    # (File-backed persistence per-path was the old shape; Postgres
    # makes persistence implicit — every store sees the same DB.)
    c = _c("py", "persisted")
    with ContributionStore() as s1:
        s1.add(c)
    with ContributionStore() as s2:
        assert s2.get(c.contribution_id) == c
