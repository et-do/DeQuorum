"""Versioned user agreements that contributors sign at signup.

An Agreement is the text of the user agreement at a specific version.
A contributor's signature over (version, text_hash) is stored in their
Contributor record; the Agreement table holds the text itself so the
signature can be reconstructed and verified later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from dequorum.core.hashing import canonical_bytes, digest


@dataclass(frozen=True, slots=True)
class AgreementVersion:
    """One version of the user agreement text."""

    version: str  # semver-ish, e.g. "1.0.0"
    text: str
    effective_at: int  # unix seconds when this version became active

    @property
    def text_hash(self) -> str:
        return digest(canonical_bytes(self.text))


# The agreement text that contributors sign at signup.
# Keep this short, plain English, and unambiguous about attestations.
SEED_AGREEMENT_V1: Final[AgreementVersion] = AgreementVersion(
    version="1.0.0",
    text=(
        "DeQuorum Contributor Agreement (v1.0.0)\n"
        "\n"
        "By signing this agreement, I attest that:\n"
        "\n"
        "1. ATTESTATION OF RIGHTS. Every contribution I submit is either:\n"
        "   (a) my own original work, OR\n"
        "   (b) content I have explicit permission to redistribute, OR\n"
        "   (c) public-domain content.\n"
        "\n"
        "2. GOOD FAITH. I will submit contributions in good faith. I will not "
        "knowingly submit false claims, plagiarized work, defamatory content, "
        "or content intended to deceive.\n"
        "\n"
        "3. LICENSE GRANT. I grant DeQuorum and any instance operator the right "
        "to display, redistribute, and reference my contributions as part of the "
        "network's inference, attribution, and ledger systems. I retain copyright "
        "in my original works.\n"
        "\n"
        "4. KICKBACK ACCEPTANCE. I understand kickbacks are distributed by the "
        "network's attribution math and may be paid in fiat currency. I "
        "acknowledge no income or revenue is guaranteed.\n"
        "\n"
        "5. KEY MANAGEMENT. I am responsible for the safety of my private "
        "signing key. The network cannot recover my key if lost.\n"
        "\n"
        "6. SIGNATURE. My Ed25519 signature over this agreement text is recorded "
        "as my acceptance and may be used to verify my attestation later."
    ),
    effective_at=0,  # set to a real timestamp once we deploy
)


SEED_AGREEMENTS: Final[tuple[AgreementVersion, ...]] = (SEED_AGREEMENT_V1,)


def current_agreement() -> AgreementVersion:
    """Return the agreement version newest contributors should sign."""
    return SEED_AGREEMENT_V1


# Backward-compatible alias for code that wants "the agreement" without
# distinguishing version. Always returns the latest.
Agreement = AgreementVersion
