from __future__ import annotations

import pytest

from dequorum.experts import Expert, ExpertRegistry


def _expert(eid: str = "e1", tags: tuple[str, ...] = ("python",)) -> Expert:
    return Expert(
        expert_id=eid,
        display_name=f"Expert {eid}",
        specialty_tags=tags,
        system_prompt=f"You are {eid}.",
        signing_key=eid.encode(),
    )


def test_registry_register_and_get() -> None:
    reg = ExpertRegistry()
    e = _expert()
    reg.register(e)
    assert reg.get("e1") is e
    assert "e1" in reg
    assert len(reg) == 1


def test_registry_rejects_duplicate_id() -> None:
    reg = ExpertRegistry()
    reg.register(_expert("dup"))
    with pytest.raises(ValueError):
        reg.register(_expert("dup"))


def test_registry_get_unknown_raises() -> None:
    with pytest.raises(KeyError):
        ExpertRegistry().get("missing")


def test_registry_by_tag_case_insensitive() -> None:
    reg = ExpertRegistry()
    reg.register(_expert("py", tags=("Python", "Typing")))
    reg.register(_expert("rs", tags=("rust",)))
    matched = reg.by_tag("python")
    assert len(matched) == 1
    assert matched[0].expert_id == "py"


def test_sign_answer_is_deterministic() -> None:
    e = _expert()
    sig1 = e.sign_answer("what is X?", "X is Y")
    sig2 = e.sign_answer("what is X?", "X is Y")
    assert sig1 == sig2


def test_sign_answer_changes_with_prompt() -> None:
    e1 = _expert("e1")
    e2 = Expert(
        expert_id="e1",
        display_name="E1",
        specialty_tags=("python",),
        system_prompt="DIFFERENT PROMPT",
        signing_key=b"e1",
    )
    sig1 = e1.sign_answer("q", "a")
    sig2 = e2.sign_answer("q", "a")
    assert sig1.digest != sig2.digest
