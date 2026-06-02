from __future__ import annotations

from dequorum.identity.agreement import current_agreement
from dequorum.identity.contributor import Contributor, Tier
from dequorum.identity.seeds import populate
from dequorum.identity.store import IdentityStore


def _make(slug: str = "alice") -> Contributor:
    return Contributor.create(
        display_name=slug.title(),
        public_key=f"pub-{slug}".encode().ljust(32, b"\x00")[:32],
        signing_key=f"priv-{slug}".encode(),
        agreement_version=current_agreement().version,
        agreement_text=current_agreement().text,
    )


def test_add_and_get_roundtrip() -> None:
    store = IdentityStore()
    c = _make()
    store.add(c)
    fetched = store.get(c.contributor_id)
    assert fetched is not None
    assert fetched.contributor_id == c.contributor_id
    assert fetched.display_name == c.display_name
    assert fetched.public_key == c.public_key
    assert fetched.tier == c.tier
    assert fetched.agreement_signature.digest == c.agreement_signature.digest


def test_seed_populate_adds_all_seed_contributors() -> None:
    store = IdentityStore()
    n = populate(store)
    assert n >= 5
    assert len(store) == n


def test_agreement_is_seeded() -> None:
    store = IdentityStore()
    agreement = store.get_agreement(current_agreement().version)
    assert agreement is not None
    assert agreement.text == current_agreement().text


def test_set_tier_updates_in_place() -> None:
    store = IdentityStore()
    c = _make()
    store.add(c)
    store.set_tier(c.contributor_id, Tier.CREDENTIALED_OR_REPUTATION)
    fetched = store.get(c.contributor_id)
    assert fetched is not None
    assert fetched.tier == Tier.CREDENTIALED_OR_REPUTATION


def test_list_all_returns_in_id_order() -> None:
    store = IdentityStore()
    for slug in ("zoe", "alice", "mike"):
        store.add(_make(slug))
    ids = [c.contributor_id for c in store.list_all()]
    assert ids == sorted(ids)
