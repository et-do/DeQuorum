"""Deterministic tests for leave-one-out marginal attribution.

Uses a fake model whose "answer" is the concatenation of the provided
contributions that share a word with the query, plus the dependency-free
HashEmbedder. That makes attribution fully deterministic: a contribution
that grounds the answer appears in it; an irrelevant or redundant one does
not change the answer, so its measured marginal value is ~0.
"""

from __future__ import annotations

from collections.abc import Iterator

from dequorum.attribution import distribute_pool, measure_attribution
from dequorum.knowledge.contribution import Contribution
from dequorum.retrieval import ScoredContribution
from dequorum.routing.embedder import HashEmbedder


class RelevanceModel:
    """Answer = the bullet-listed contributions whose text shares a token
    with the query. A redundant duplicate doesn't change the answer."""

    def complete(self, system: str, user: str) -> str:
        bullets = [ln[2:] for ln in system.splitlines() if ln.startswith("- ")]
        q = set(user.lower().split())
        kept = [b for b in bullets if set(b.lower().split()) & q]
        # Like a real model, state each distinct fact once — identical
        # (duplicate) contributions don't get restated twice.
        seen: set[str] = set()
        unique = [b for b in kept if not (b in seen or seen.add(b))]
        return " ".join(unique) if unique else "no grounding available"

    def stream(self, system: str, user: str) -> Iterator[str]:
        yield self.complete(system, user)


def _scored(
    text: str, score: float, contributor: str, version: int = 1
) -> ScoredContribution:
    c = Contribution.create(
        contributor_id=contributor,
        text=text,
        citations=(),
        signing_key=b"test-key",
        primary_category_id="cat",
        lineage_id="lin:fixed",
        version_number=version,
    )
    return ScoredContribution(contribution=c, score=score)


_QUERY = "explain quasar entanglement and neutron star mergers"
_X = "quasar entanglement spectroscopy reveals photon correlations"
_Y = "neutron star mergers emit gravitational waves and kilonova light"


def _credits(retrieved):
    return measure_attribution(
        query=_QUERY,
        persona_prompt="You are a physics assistant.",
        retrieved=retrieved,
        model=RelevanceModel(),
        embedder=HashEmbedder(512),
    )


def test_relevant_contribution_outscores_irrelevant() -> None:
    retrieved = [
        _scored(_X, 0.9, "alice"),
        _scored("sourdough fermentation needs flour water salt time", 0.1, "bob"),
    ]
    credits = _credits(retrieved)
    rel = next(c for c in credits if c.contributor_id == "alice")
    irrel = next(c for c in credits if c.contributor_id == "bob")
    assert rel.marginal_value > irrel.marginal_value
    assert rel.credit_weight > irrel.credit_weight
    assert abs(sum(c.credit_weight for c in credits) - 1.0) < 1e-6
    assert all(c.credit_weight >= 0 for c in credits)


def test_empty_retrieved_yields_no_credits() -> None:
    assert _credits([]) == []


def _flat_shares(retrieved) -> dict[str, float]:
    """The naive ledger: every citation gets 1/k, aggregated by contributor."""
    n = len(retrieved)
    shares: dict[str, float] = {}
    for sc in retrieved:
        cid = sc.contribution.contributor_id
        shares[cid] = shares.get(cid, 0.0) + 1.0 / n
    return shares


def test_duplicate_stuffing_does_not_inflate_marginal_share() -> None:
    """Core gaming-resistance result: under flat credit, a contributor can
    inflate their share by submitting a near-duplicate; under marginal
    credit they cannot, because the duplicate carries no new value."""
    honest = [_scored(_X, 0.9, "alice"), _scored(_Y, 0.8, "bob")]
    gamed = [
        _scored(_X, 0.9, "alice", version=1),
        _scored(_X, 0.85, "alice", version=2),  # near-duplicate, same content
        _scored(_Y, 0.8, "bob"),
    ]

    # Flat credit IS gameable: alice's share goes up just by duplicating.
    flat_honest = _flat_shares(honest)["alice"]
    flat_gamed = _flat_shares(gamed)["alice"]
    assert flat_gamed > flat_honest  # 2/3 > 1/2

    # Marginal credit is NOT: duplicating does not increase alice's share.
    marg_honest = distribute_pool(_credits(honest), 1.0).get("alice", 0.0)
    marg_gamed = distribute_pool(_credits(gamed), 1.0).get("alice", 0.0)
    assert marg_gamed <= marg_honest + 1e-9


def test_distribute_pool_aggregates_by_contributor() -> None:
    retrieved = [_scored(_X, 0.9, "alice"), _scored(_Y, 0.8, "alice")]
    payouts = distribute_pool(_credits(retrieved), pool=100.0)
    assert set(payouts) == {"alice"}
    assert abs(payouts["alice"] - 100.0) < 1e-6
