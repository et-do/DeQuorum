"""Base model interface + Ollama HTTP client + a deterministic mock for tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib import error, request

from ai_playground.core.errors import CompositionError


class BaseModel(Protocol):
    def complete(self, system: str, user: str) -> str: ...


@dataclass(frozen=True, slots=True)
class OllamaBaseModel:
    """Talks to a local Ollama server. Defaults match Ollama's install defaults."""

    model: str = "qwen2.5-coder:7b"
    host: str = "http://localhost:11434"
    timeout_seconds: float = 120.0

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0.0},
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


@dataclass(frozen=True, slots=True)
class MockBaseModel:
    """Deterministic mock: returns a templated response. Useful for tests + CI."""

    label: str = "mock"

    def complete(self, system: str, user: str) -> str:
        stripped = system.strip()
        snippet = stripped.splitlines()[0][:60] if stripped else "(none)"
        return f"[{self.label}] system={snippet!r} user={user!r}"
