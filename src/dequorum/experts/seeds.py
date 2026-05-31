"""Seed experts for the OSS code knowledge MVP."""

from __future__ import annotations

from dequorum.experts import Expert, ExpertRegistry


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
    example_questions=(
        "How do I type a generator function?",
        "How do I use ParamSpec to forward decorator signatures?",
        "What does TypeVar bound vs constraint mean?",
        "How do Protocol and ABC differ for structural subtyping?",
        "How do I type an async iterator?",
        "What's the difference between Optional and Union?",
        "How do I add type hints to a dataclass?",
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
    example_questions=(
        "What's the difference between asyncio.gather and asyncio.wait?",
        "How does asyncio.create_task differ from awaiting a coroutine directly?",
        "When should I use Trio's nursery instead of asyncio?",
        "How do I cancel an in-flight async operation safely?",
        "What does anyio.to_thread.run_sync actually do?",
        "Why is my coroutine 'never awaited'?",
        "How does the GIL interact with asyncio?",
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
    example_questions=(
        "What's the difference between pip and pipx?",
        "When should I use uv instead of pip?",
        "What does PEP 660 say about editable installs?",
        "Should I use hatchling, setuptools, or flit as my build backend?",
        "How do I declare optional dependencies in pyproject.toml?",
        "What's the difference between sdist and wheel?",
        "How do dependency groups work in PEP 735?",
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
    example_questions=(
        "What are Rust's ownership rules?",
        "How does Rust's match expression work with enums?",
        "When do I need to write explicit lifetime annotations?",
        "Why can't I have a mutable and immutable reference at the same time?",
        "What's the difference between Copy and Clone?",
        "How does Box<T> differ from Rc<T> and Arc<T>?",
        "When should I use a trait object vs a generic?",
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
    example_questions=(
        "What protocol does HTTP/3 run on?",
        "What is HTTP/2 server push and why was it deprecated?",
        "What's the difference between PUT and PATCH?",
        "How do HTTP cookies work cross-origin?",
        "When does a server return 401 vs 403?",
        "What does Cache-Control: immutable mean?",
        "How does HSTS preload work?",
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
