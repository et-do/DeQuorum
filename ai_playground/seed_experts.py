"""Seed experts for the OSS code knowledge MVP."""

from __future__ import annotations

from ai_playground.experts import Expert, ExpertRegistry


def _seed_key(slug: str) -> bytes:
    return f"dev-seed-key-{slug}".encode()


PYTHON_TYPING = Expert(
    expert_id="python-typing",
    display_name="Python Typing Specialist",
    specialty_tags=(
        "python",
        "typing",
        "types",
        "annotations",
        "mypy",
        "pyright",
        "generic",
        "generics",
        "protocol",
        "pep484",
        "pep526",
        "pep612",
        "pep695",
    ),
    system_prompt=(
        "You are a Python typing specialist. Answer using only the semantics defined "
        "in PEP 484, PEP 526, PEP 604, PEP 612, and PEP 695. Always cite which PEP "
        "or which stdlib module backs each claim. If a question is outside Python "
        "typing, say so explicitly rather than guessing."
    ),
    signing_key=_seed_key("python-typing"),
)

PYTHON_ASYNC = Expert(
    expert_id="python-async",
    display_name="Python Async/Concurrency Specialist",
    specialty_tags=(
        "python",
        "async",
        "asyncio",
        "await",
        "concurrency",
        "coroutine",
        "trio",
        "anyio",
        "event",
        "loop",
        "task",
        "future",
    ),
    system_prompt=(
        "You are a Python concurrency specialist. Answer about asyncio, trio, and "
        "anyio with reference to the cpython source or the official docs. Distinguish "
        "between coroutines, tasks, and futures precisely. If the user is conflating "
        "threading with async, correct them."
    ),
    signing_key=_seed_key("python-async"),
)

PYTHON_PACKAGING = Expert(
    expert_id="python-packaging",
    display_name="Python Packaging Specialist",
    specialty_tags=(
        "python",
        "packaging",
        "pip",
        "uv",
        "poetry",
        "pyproject",
        "wheel",
        "sdist",
        "pep517",
        "pep518",
        "pep621",
        "pep660",
        "dependency",
        "metadata",
    ),
    system_prompt=(
        "You are a Python packaging specialist. Answer with reference to PEP 517/518/"
        "621/660 and the PyPA specifications. Be precise about the difference between "
        "build backends (hatchling, setuptools, flit) and frontends (pip, uv, poetry). "
        "If a question requires running code, say so."
    ),
    signing_key=_seed_key("python-packaging"),
)

RUST_OWNERSHIP = Expert(
    expert_id="rust-ownership",
    display_name="Rust Ownership and Lifetimes Specialist",
    specialty_tags=(
        "rust",
        "ownership",
        "borrow",
        "borrowing",
        "lifetime",
        "lifetimes",
        "move",
        "reference",
        "mutable",
        "rustc",
    ),
    system_prompt=(
        "You are a Rust ownership and lifetimes specialist. Answer with reference to "
        "the Rust Reference and Rustonomicon. Be precise about the distinctions "
        "between owned, borrowed, mutably-borrowed, and moved values. If the user is "
        "asking about Rust async, say so and decline."
    ),
    signing_key=_seed_key("rust-ownership"),
)

HTTP_PROTOCOL = Expert(
    expert_id="http-protocol",
    display_name="HTTP Protocol Specialist",
    specialty_tags=(
        "http",
        "https",
        "http1",
        "http2",
        "http3",
        "rest",
        "header",
        "headers",
        "status",
        "method",
        "tls",
        "cookie",
        "rfc",
    ),
    system_prompt=(
        "You are an HTTP protocol specialist. Answer with reference to the relevant "
        "RFCs (9110, 9111, 9112, 9113, 9114). Be precise about the differences "
        "between HTTP/1.1, HTTP/2, and HTTP/3. If a question is about a specific "
        "framework rather than the protocol, say so."
    ),
    signing_key=_seed_key("http-protocol"),
)


_SEED_EXPERTS = (
    PYTHON_TYPING,
    PYTHON_ASYNC,
    PYTHON_PACKAGING,
    RUST_OWNERSHIP,
    HTTP_PROTOCOL,
)


def build_seed_registry() -> ExpertRegistry:
    registry = ExpertRegistry()
    for expert in _SEED_EXPERTS:
        registry.register(expert)
    return registry
