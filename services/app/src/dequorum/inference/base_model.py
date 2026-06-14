"""Base model interface + Ollama HTTP client + a deterministic mock for tests."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol
from urllib import error, request

from dequorum.core.errors import CompositionError


class BaseModel(Protocol):
    def complete(self, system: str, user: str) -> str: ...
    def stream(self, system: str, user: str) -> Iterator[str]: ...


@dataclass(frozen=True, slots=True)
class OllamaBaseModel:
    """Talks to a local Ollama server.

    `model` accepts either a registered model_id (e.g. "qwen2.5-coder-7b") or
    a raw Ollama tag (e.g. "qwen2.5-coder:7b"). Use registered ids when you
    want the swap-via-config behavior; raw tags are an escape hatch.
    """

    model: str = ""  # empty = look up the default from inference/models.py
    host: str = "http://localhost:11434"
    timeout_seconds: float = 120.0
    # Bound generation length. CPU inference cost scales linearly with the
    # number of tokens produced, so an uncapped reply (a chatty 7B model
    # happily pads a greeting to 100+ tokens) can run ~15-20s. 512 tokens
    # covers virtually every chat answer while capping the worst case.
    num_predict: int = 512

    def _resolved_tag(self) -> str:
        from dequorum.inference.models import DEFAULT_BASE_MODEL_ID, resolve_ollama_tag

        return resolve_ollama_tag(self.model or DEFAULT_BASE_MODEL_ID)

    def _options(self) -> dict:
        return {"temperature": 0.0, "num_predict": self.num_predict}

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self._resolved_tag(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": self._options(),
            # Keep the model resident in VRAM across requests. Default
            # is 5 minutes; pinning at 30m means a paused user doesn't
            # pay the model-load cost on their next message.
            "keep_alive": "30m",
        }
        req = request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = json.loads(resp.read().decode())
        except (error.URLError, TimeoutError) as exc:
            raise CompositionError(
                f"Ollama unreachable at {self.host} (is `ollama serve` running?): {exc}"
            ) from exc

        message = body.get("message", {})
        content = message.get("content")
        if not content:
            raise CompositionError(f"Ollama returned no content: {body!r}")
        return str(content)

    def stream(self, system: str, user: str) -> Iterator[str]:
        """Stream incremental message-content chunks from Ollama's
        `/api/chat` endpoint with `stream: true`. Each NDJSON line carries
        an incremental `message.content` delta; we yield those as-is.
        """
        payload = {
            "model": self._resolved_tag(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": True,
            "options": self._options(),
            "keep_alive": "30m",
        }
        req = request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            resp = request.urlopen(req, timeout=self.timeout_seconds)
        except (error.URLError, TimeoutError) as exc:
            raise CompositionError(f"Ollama unreachable at {self.host}: {exc}") from exc
        try:
            for raw in resp:
                line = raw.decode().strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
                if data.get("done"):
                    break
        finally:
            resp.close()


@dataclass(frozen=True, slots=True)
class OpenAICompatibleModel:
    """Talks to any OpenAI-compatible `/chat/completions` endpoint.

    One client covers Groq, DeepInfra, Together, Fireworks, OpenRouter, vLLM, and
    Ollama's own `/v1` — they all speak the same wire format, so switching providers
    is just a `base_url` + `api_key` + `model` change. This is how the network serves
    an *open* model from a fast hosted provider without leaving the open-model lane
    (the 1-minute self-hosted-Ollama latency is a self-hosting artifact, not a tax on
    open weights).

    Responsibility note: the operator must point this at an openly-licensed model
    (Apache-2.0 / MIT — Qwen, Mistral, OLMo, …). A user-supplied key pointing at a
    closed model is *serving-only*; closed-model output must never feed the
    contribution corpus or distillation (their terms forbid training competing
    models). See docs/architecture/model-serving.md.
    """

    model: str
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    timeout_seconds: float = 120.0
    num_predict: int = 512

    def _payload(self, system: str, user: str, *, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": stream,
            "temperature": 0.0,
            "max_tokens": self.num_predict,
        }

    def _request(self, payload: dict) -> request.Request:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode(),
            headers=headers,
        )

    def complete(self, system: str, user: str) -> str:
        req = self._request(self._payload(system, user, stream=False))
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = json.loads(resp.read().decode())
        except (error.URLError, TimeoutError) as exc:
            raise CompositionError(
                f"Model provider unreachable at {self.base_url}: {exc}"
            ) from exc
        choices = body.get("choices") or []
        content = choices[0].get("message", {}).get("content") if choices else None
        if not content:
            raise CompositionError(f"Provider returned no content: {body!r}")
        return str(content)

    def stream(self, system: str, user: str) -> Iterator[str]:
        """Yield incremental content deltas from an SSE `chat/completions` stream.

        Each event is a `data: {json}` line; `data: [DONE]` terminates the stream.
        """
        req = self._request(self._payload(system, user, stream=True))
        try:
            resp = request.urlopen(req, timeout=self.timeout_seconds)
        except (error.URLError, TimeoutError) as exc:
            raise CompositionError(
                f"Model provider unreachable at {self.base_url}: {exc}"
            ) from exc
        try:
            for raw in resp:
                line = raw.decode().strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = (obj.get("choices") or [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content
        finally:
            resp.close()


@dataclass(frozen=True, slots=True)
class MockBaseModel:
    """Deterministic mock: returns a templated response. Useful for tests + CI."""

    label: str = "mock"
    # Tunable for tests that want fast streaming.
    chunk_delay_seconds: float = 0.0

    def complete(self, system: str, user: str) -> str:
        stripped = system.strip()
        snippet = stripped.splitlines()[0][:60] if stripped else "(none)"
        return f"[{self.label}] system={snippet!r} user={user!r}"

    def stream(self, system: str, user: str) -> Iterator[str]:
        full = self.complete(system, user)
        # Yield ~6-char chunks so callers exercise their stream-handling
        # path; with chunk_delay_seconds=0 this is effectively instant.
        for i in range(0, len(full), 6):
            yield full[i : i + 6]
            if self.chunk_delay_seconds > 0:
                time.sleep(self.chunk_delay_seconds)
