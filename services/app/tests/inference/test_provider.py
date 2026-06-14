from __future__ import annotations

import json

import pytest

from dequorum.core.errors import CompositionError
from dequorum.inference import base_model as bm
from dequorum.inference.base_model import (
    MockBaseModel,
    OllamaBaseModel,
    OpenAICompatibleModel,
)
from dequorum.inference.provider import build_serving_model


def test_provider_selection() -> None:
    assert isinstance(build_serving_model(use_mock=True), MockBaseModel)
    assert isinstance(build_serving_model(provider="ollama"), OllamaBaseModel)
    m = build_serving_model(
        provider="openai", base_url="https://api.x.com/v1", model="qwen", api_key="k"
    )
    assert isinstance(m, OpenAICompatibleModel)


def test_openai_provider_requires_base_url_and_model() -> None:
    with pytest.raises(CompositionError):
        build_serving_model(provider="openai", model="qwen")  # no base_url
    with pytest.raises(CompositionError):
        build_serving_model(provider="openai", base_url="https://x/v1")  # no model


def test_unknown_provider_rejected() -> None:
    with pytest.raises(CompositionError):
        build_serving_model(provider="bogus")


class _Resp:
    def __init__(self, body: bytes) -> None:
        self._b = body

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *a: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._b


def test_openai_complete_parses_content_and_payload(monkeypatch) -> None:
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode())
        captured["url"] = req.full_url
        captured["auth"] = req.headers.get("Authorization")
        return _Resp(
            json.dumps(
                {"choices": [{"message": {"content": "QUIC over UDP"}}]}
            ).encode()
        )

    monkeypatch.setattr(bm.request, "urlopen", fake_urlopen)
    m = OpenAICompatibleModel(
        model="qwen", base_url="https://api.x.com/v1", api_key="sk-1", num_predict=64
    )
    assert m.complete(system="S", user="U") == "QUIC over UDP"

    body = captured["body"]
    assert body["model"] == "qwen"
    assert body["temperature"] == 0.0  # deterministic, reproducible
    assert body["max_tokens"] == 64
    assert body["messages"] == [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "U"},
    ]
    assert captured["url"].endswith("/v1/chat/completions")
    assert captured["auth"] == "Bearer sk-1"


class _StreamResp:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    def __iter__(self):
        return iter(self._lines)

    def close(self) -> None:
        pass


def test_openai_stream_parses_sse_and_stops_at_done(monkeypatch) -> None:
    lines = [
        b'data: {"choices":[{"delta":{"content":"QUIC"}}]}\n',
        b"\n",  # blank keep-alive line, ignored
        b'data: {"choices":[{"delta":{"content":" over UDP"}}]}\n',
        b"data: [DONE]\n",
        b'data: {"choices":[{"delta":{"content":"AFTER-DONE"}}]}\n',
    ]
    monkeypatch.setattr(
        bm.request, "urlopen", lambda req, timeout=None: _StreamResp(lines)
    )
    m = OpenAICompatibleModel(model="qwen", base_url="https://api.x.com/v1")
    out = "".join(m.stream(system="S", user="U"))
    assert out == "QUIC over UDP"  # [DONE] terminates; nothing after is read
