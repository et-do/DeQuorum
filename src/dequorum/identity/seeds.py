"""Seed contributors for the v0.1 demo.

In v0.1, each seed expert maps 1:1 to a seed contributor — the persona
publishes under itself. In v0.2+, real contributors will publish under
one or more expert personas via the contributor_experts M:N table.
"""

from __future__ import annotations

from dequorum.identity.agreement import current_agreement
from dequorum.identity.contributor import Contributor, Tier
from dequorum.identity.store import IdentityStore


def _seed_public_key(slug: str) -> bytes:
    """Pseudo-public-key: deterministic but unique per slug. Real signups use WebCrypto."""
    return f"dev-seed-pubkey-{slug}".encode().ljust(32, b"\x00")[:32]


def _seed_private_key(slug: str) -> bytes:
    return f"dev-seed-key-{slug}".encode()


SEED_CONTRIBUTOR_SLUGS: tuple[str, ...] = (
    "python-typing",
    "python-async",
    "python-packaging",
    "rust-ownership",
    "http-protocol",
)


def build_seed_contributors() -> list[Contributor]:
    """Construct seed contributors that mirror the seed experts 1:1."""
    agreement = current_agreement()
    contributors: list[Contributor] = []
    for slug in SEED_CONTRIBUTOR_SLUGS:
        pub = _seed_public_key(slug)
        priv = _seed_private_key(slug)
        contributor = Contributor.create(
            display_name=slug.replace("-", " ").title(),
            public_key=pub,
            signing_key=priv,
            agreement_version=agreement.version,
            agreement_text=agreement.text,
            tier=Tier.SOCIAL_PROOF,  # seed contributors get Tier 2 by fiat
            created_at=0,
        )
        contributors.append(contributor)
    return contributors


def populate(store: IdentityStore) -> int:
    """Insert all seed contributors into the store."""
    contributors = build_seed_contributors()
    for c in contributors:
        store.add(c)
    return len(contributors)


def seed_contributor_for(slug: str) -> tuple[Contributor, bytes]:
    """Return (Contributor, private_key) for a seed-expert slug.

    The same slug always produces the same Contributor (and same id), so this
    is safe to call from anywhere that needs to reconstruct a seed contributor.
    """
    pub = _seed_public_key(slug)
    priv = _seed_private_key(slug)
    agreement = current_agreement()
    contributor = Contributor.create(
        display_name=slug.replace("-", " ").title(),
        public_key=pub,
        signing_key=priv,
        agreement_version=agreement.version,
        agreement_text=agreement.text,
        tier=Tier.SOCIAL_PROOF,
    )
    return contributor, priv


def contributor_id_for(slug: str) -> str:
    """Resolve a seed-expert slug to its contributor_id."""
    contributor, _ = seed_contributor_for(slug)
    return contributor.contributor_id
