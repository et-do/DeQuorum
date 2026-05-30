"""Seed contributions: verified factual claims attached to each seed expert.

These exist so a fresh checkout has something to retrieve from immediately.
In production, real contributors submit these themselves via the `submit` CLI.
"""

from __future__ import annotations

from ai_playground.contribution_store import ContributionStore
from ai_playground.contributions import Contribution
from ai_playground.seed_experts import (
    HTTP_PROTOCOL,
    PYTHON_ASYNC,
    PYTHON_PACKAGING,
    PYTHON_TYPING,
    RUST_OWNERSHIP,
)

# Each tuple: (text, citations). For seed data, contributor_id == expert_id.

_PYTHON_TYPING_FACTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "A generator function's return type annotation uses "
        "Generator[YieldType, SendType, ReturnType] from typing. "
        "The send type is None when the generator does not consume sent values.",
        ("https://peps.python.org/pep-0484/",),
    ),
    (
        "PEP 526 introduced variable annotations (the `x: int = 0` syntax). "
        "It does NOT cover generator return types — that semantics lives in PEP 484.",
        ("https://peps.python.org/pep-0526/",),
    ),
    (
        "PEP 695 introduced the `type` statement and PEP 696 introduced "
        "TypeVar defaults. Both are stable in Python 3.12 / 3.13.",
        ("https://peps.python.org/pep-0695/", "https://peps.python.org/pep-0696/"),
    ),
    (
        "PEP 612 introduced ParamSpec for forwarding parameter signatures "
        "through decorators while preserving type information.",
        ("https://peps.python.org/pep-0612/",),
    ),
    (
        "typing.Protocol (PEP 544) enables structural subtyping. A class need not "
        "inherit from a Protocol to satisfy it — matching method signatures suffice.",
        ("https://peps.python.org/pep-0544/",),
    ),
)

_PYTHON_ASYNC_FACTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "asyncio.create_task(coro) schedules the coroutine onto the currently "
        "running event loop and returns a Task object. It raises RuntimeError "
        "if no loop is running.",
        ("https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task",),
    ),
    (
        "asyncio.gather returns when all awaitables complete (or any raises with "
        "return_exceptions=False). asyncio.wait returns sets of (done, pending) tasks "
        "after a configurable condition — they are NOT interchangeable.",
        ("https://docs.python.org/3/library/asyncio-task.html#asyncio.gather",),
    ),
    (
        "Trio implements structured concurrency: every task lives inside a nursery "
        "and the nursery cannot exit until all child tasks finish. This is a "
        "stronger guarantee than asyncio's flat task scheduling.",
        (
            "https://trio.readthedocs.io/en/stable/reference-core.html#tasks-let-you-do-multiple-things-at-once",
        ),
    ),
    (
        "anyio provides one API that runs on either asyncio or trio backends. "
        "Library authors should target anyio if they want backend independence.",
        ("https://anyio.readthedocs.io/",),
    ),
    (
        "A coroutine is a Future-like object created by calling an async function. "
        "It does nothing until awaited or wrapped in a Task. Conflating coroutines and "
        "Tasks is the most common cause of 'coroutine was never awaited' warnings.",
        ("https://docs.python.org/3/library/asyncio-task.html",),
    ),
)

_PYTHON_PACKAGING_FACTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "pyproject.toml's [build-system] table is specified by PEP 518; "
        "the [project] table is PEP 621.",
        ("https://peps.python.org/pep-0518/", "https://peps.python.org/pep-0621/"),
    ),
    (
        "PEP 660 defines editable installs via the build backend (pip install -e), "
        "replacing the legacy setup.py develop mechanism.",
        ("https://peps.python.org/pep-0660/",),
    ),
    (
        "uv is implemented in Rust; for typical lockfile + install operations it "
        "is 10-100x faster than pip while remaining wire-compatible with PyPI.",
        ("https://docs.astral.sh/uv/",),
    ),
    (
        "A wheel (.whl) is a pre-built binary distribution; sdist (.tar.gz) is the "
        "source distribution. pip prefers wheels because they skip the build step.",
        ("https://packaging.python.org/en/latest/discussions/package-formats/",),
    ),
    (
        "Hatchling is the build backend recommended by PyPA as of 2024-2026. "
        "Setuptools is still maintained but setup.py-style configuration is legacy.",
        ("https://hatch.pypa.io/latest/",),
    ),
)

_RUST_OWNERSHIP_FACTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Rust's ownership rules: each value has exactly one owner; when the owner "
        "goes out of scope, the value is dropped. This is what makes Rust memory-safe "
        "without a garbage collector.",
        ("https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html",),
    ),
    (
        "Borrow rules: at any time you can have either one mutable reference (&mut T) "
        "OR any number of immutable references (&T), but never both. This is enforced "
        "at compile time by the borrow checker.",
        ("https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html",),
    ),
    (
        "Lifetimes annotate how long references are valid. They don't affect runtime; "
        "the compiler uses them to verify a reference doesn't outlive its target.",
        ("https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html",),
    ),
    (
        "Types implementing Copy are duplicated on assignment instead of moved. "
        "Most primitive types are Copy; String, Vec, and Box are not.",
        ("https://doc.rust-lang.org/std/marker/trait.Copy.html",),
    ),
    (
        "The Drop trait runs custom code when a value goes out of scope. "
        "Drop::drop is called automatically; calling it manually is a compile error.",
        ("https://doc.rust-lang.org/std/ops/trait.Drop.html",),
    ),
)

_HTTP_FACTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "RFC 9110 defines core HTTP semantics independent of version. RFC 9111 covers "
        "caching; 9112 is HTTP/1.1; 9113 is HTTP/2; 9114 is HTTP/3.",
        ("https://www.rfc-editor.org/rfc/rfc9110.html",),
    ),
    (
        "HTTP/2 uses a single multiplexed connection with binary framing. Multiple "
        "requests can fly on the same connection without head-of-line blocking at "
        "the HTTP layer (though TCP HOL still applies).",
        ("https://www.rfc-editor.org/rfc/rfc9113.html",),
    ),
    (
        "HTTP/3 runs over QUIC (UDP-based), eliminating TCP head-of-line blocking. "
        "Connection setup is faster because QUIC merges transport and TLS handshakes.",
        ("https://www.rfc-editor.org/rfc/rfc9114.html",),
    ),
    (
        "The Strict-Transport-Security header (HSTS) tells the browser to use HTTPS "
        "for all future requests to the origin for the duration of max-age.",
        ("https://www.rfc-editor.org/rfc/rfc6797.html",),
    ),
    (
        "CORS is enforced by the browser, not the server. The server's "
        "Access-Control-Allow-Origin header tells the browser whether a "
        "cross-origin response may be read by the requesting page's JavaScript.",
        ("https://fetch.spec.whatwg.org/#cors-protocol",),
    ),
)


def _build_contributions(
    expert_id: str,
    signing_key: bytes,
    facts: tuple[tuple[str, tuple[str, ...]], ...],
) -> list[Contribution]:
    return [
        Contribution.create(
            expert_id=expert_id,
            contributor_id=expert_id,
            text=text,
            citations=citations,
            signing_key=signing_key,
        )
        for text, citations in facts
    ]


def seed_contributions() -> list[Contribution]:
    """Return the full list of seed contributions across all seed experts."""
    out: list[Contribution] = []
    out.extend(
        _build_contributions(
            PYTHON_TYPING.expert_id, PYTHON_TYPING.signing_key, _PYTHON_TYPING_FACTS
        )
    )
    out.extend(
        _build_contributions(
            PYTHON_ASYNC.expert_id, PYTHON_ASYNC.signing_key, _PYTHON_ASYNC_FACTS
        )
    )
    out.extend(
        _build_contributions(
            PYTHON_PACKAGING.expert_id,
            PYTHON_PACKAGING.signing_key,
            _PYTHON_PACKAGING_FACTS,
        )
    )
    out.extend(
        _build_contributions(
            RUST_OWNERSHIP.expert_id, RUST_OWNERSHIP.signing_key, _RUST_OWNERSHIP_FACTS
        )
    )
    out.extend(
        _build_contributions(
            HTTP_PROTOCOL.expert_id, HTTP_PROTOCOL.signing_key, _HTTP_FACTS
        )
    )
    return out


def populate(store: ContributionStore) -> int:
    """Insert all seed contributions into the store. Returns the count added."""
    contribs = seed_contributions()
    for c in contribs:
        store.add(c)
    return len(contribs)
