from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from dequorum.base_model import MockBaseModel, OllamaBaseModel
from dequorum.core.errors import CompositionError


class _FakeResp:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_mock_model_is_deterministic() -> None:
    m = MockBaseModel()
    assert m.complete("sys", "user") == m.complete("sys", "user")
    assert "user" in m.complete("sys", "user")


def test_mock_model_distinguishes_system_and_user() -> None:
    m = MockBaseModel()
    r1 = m.complete("system A", "query")
    r2 = m.complete("system B", "query")
    assert r1 != r2


def test_ollama_parses_chat_response() -> None:
    payload = {"message": {"role": "assistant", "content": "hello world"}}
    target = "dequorum.base_model.request.urlopen"
    with patch(target, return_value=_FakeResp(payload)):
        result = OllamaBaseModel().complete("sys", "user")
    assert result == "hello world"


def test_ollama_raises_on_empty_content() -> None:
    payload = {"message": {"role": "assistant", "content": ""}}
    target = "dequorum.base_model.request.urlopen"
    with patch(target, return_value=_FakeResp(payload)):
        with pytest.raises(CompositionError):
            OllamaBaseModel().complete("sys", "user")


def test_ollama_raises_on_connection_failure() -> None:
    from urllib.error import URLError

    target = "dequorum.base_model.request.urlopen"
    with patch(target, side_effect=URLError("refused")):
        with pytest.raises(CompositionError, match="Ollama unreachable"):
            OllamaBaseModel().complete("sys", "user")
