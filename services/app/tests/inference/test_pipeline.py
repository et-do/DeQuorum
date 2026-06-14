from __future__ import annotations

from dequorum.core.crypto import generate_signing_key
from dequorum.inference.pipeline import _augment_system_prompt
from dequorum.knowledge.contribution import Contribution


def _contrib(text: str) -> Contribution:
    return Contribution.create(
        contributor_id="dq:t",
        text=text,
        citations=(),
        signing_key=generate_signing_key(),
        primary_category_id="bench",
    )


def test_no_contributions_returns_base_prompt() -> None:
    assert _augment_system_prompt("PERSONA", ()) == "PERSONA"


def test_grounded_prompt_separates_instructions_from_data() -> None:
    """The grounding prompt must frame references as DATA, not instructions — the
    injection defense from whitepaper §8.8. It must keep the base persona and the
    contribution's factual text while telling the model not to follow embedded
    instructions."""
    c = _contrib("HTTP/3 runs over QUIC, which runs over UDP.")
    out = _augment_system_prompt("PERSONA", (c,))

    assert out.startswith("PERSONA")  # persona preserved
    assert "QUIC" in out  # factual content still grounded
    # instruction-data separation language is present (the hardening)
    low = out.lower()
    assert "data" in low and "never follow" in low
    # the vulnerable "trusted" framing is gone
    assert "trusted background" not in low
