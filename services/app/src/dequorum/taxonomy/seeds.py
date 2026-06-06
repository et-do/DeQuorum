"""Seed category taxonomy for v0.1.

The curated taxonomy is intentionally small at launch. Per
contributor-intake.md §4, new top-level categories are added via Tier
3 reviewer vote; this seed tree is just what we ship pre-populated so
the network has a starting structure to grow from.

Five of the seed leaves carry a persona (system_prompt, specialty
tags, example questions). These are the "routable" categories — the
ones the router can pick as the target for an incoming question. The
rest of the tree is organizational only.
"""

from __future__ import annotations

from typing import Final

from dequorum.taxonomy.category import Category
from dequorum.taxonomy.store import CategoryStore

# Sentinel for legacy / not-yet-categorized contributions.
UNCATEGORIZED_ID: Final[str] = "uncategorized"


# (category_id, display_name, description, system_prompt, specialty_tags,
#  example_questions).
# Parent is derived from the slash structure of category_id.
_SEED_TREE: tuple[tuple[str, str, str, str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        UNCATEGORIZED_ID,
        "Uncategorized",
        "Legacy or unassigned contributions.",
        "",
        (),
        (),
    ),
    # Programming
    (
        "programming",
        "Programming",
        "Software development across all languages and platforms.",
        "",
        (),
        (),
    ),
    (
        "programming/python",
        "Python",
        "The Python language and standard library.",
        "",
        (),
        (),
    ),
    (
        "programming/python/typing",
        "Python — Typing",
        "PEPs 484, 526, 612, 695; mypy; pyright.",
        (
            "You are a Python typing specialist. Answer using the semantics "
            "defined in PEP 484, PEP 526, PEP 604, PEP 612, and PEP 695. "
            "Reference the relevant PEP or stdlib module when grounding a "
            "claim. If a question is outside Python typing, answer plainly "
            "without forcing a typing frame."
        ),
        (
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
        (
            "How do I type a generator function?",
            "How do I use ParamSpec to forward decorator signatures?",
            "What does TypeVar bound vs constraint mean?",
            "How do Protocol and ABC differ for structural subtyping?",
            "How do I type an async iterator?",
            "What's the difference between Optional and Union?",
            "How do I add type hints to a dataclass?",
        ),
    ),
    (
        "programming/python/async",
        "Python — Async",
        "asyncio, trio, anyio, coroutines, event loop.",
        (
            "You are a Python concurrency specialist. Answer about asyncio, "
            "trio, and anyio with reference to the cpython source or the "
            "official docs. Distinguish coroutines, tasks, and futures "
            "precisely. If a user is conflating threading with async, "
            "correct them."
        ),
        (
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
        (
            "What's the difference between asyncio.gather and asyncio.wait?",
            "How does asyncio.create_task differ from awaiting a coroutine directly?",
            "When should I use Trio's nursery instead of asyncio?",
            "How do I cancel an in-flight async operation safely?",
            "What does anyio.to_thread.run_sync actually do?",
            "Why is my coroutine 'never awaited'?",
            "How does the GIL interact with asyncio?",
        ),
    ),
    (
        "programming/python/packaging",
        "Python — Packaging",
        "pip, uv, pyproject.toml, wheels.",
        (
            "You are a Python packaging specialist. Answer with reference to "
            "PEP 517/518/621/660 and the PyPA specifications. Be precise "
            "about the difference between build backends (hatchling, "
            "setuptools, flit) and frontends (pip, uv, poetry)."
        ),
        (
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
        (
            "What's the difference between pip and pipx?",
            "When should I use uv instead of pip?",
            "What does PEP 660 say about editable installs?",
            "Should I use hatchling, setuptools, or flit as my build backend?",
            "How do I declare optional dependencies in pyproject.toml?",
            "What's the difference between sdist and wheel?",
            "How do dependency groups work in PEP 735?",
        ),
    ),
    ("programming/rust", "Rust", "The Rust language and core ecosystem.", "", (), ()),
    (
        "programming/rust/ownership",
        "Rust — Ownership",
        "Borrow checker, lifetimes, move semantics.",
        (
            "You are a Rust ownership and lifetimes specialist. Answer with "
            "reference to the Rust Reference and Rustonomicon. Be precise "
            "about the distinctions between owned, borrowed, mutably-"
            "borrowed, and moved values."
        ),
        (
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
        (
            "What are Rust's ownership rules?",
            "How does Rust's match expression work with enums?",
            "When do I need to write explicit lifetime annotations?",
            "Why can't I have a mutable and immutable reference at the same time?",
            "What's the difference between Copy and Clone?",
            "How does Box<T> differ from Rc<T> and Arc<T>?",
            "When should I use a trait object vs a generic?",
        ),
    ),
    (
        "programming/javascript",
        "JavaScript",
        "JS / TypeScript / Node / browser runtime.",
        "",
        (),
        (),
    ),
    ("programming/go", "Go", "The Go language and runtime.", "", (), ()),
    # Web & protocols
    (
        "web-and-protocols",
        "Web & Protocols",
        "Network protocols, web standards, formats.",
        "",
        (),
        (),
    ),
    (
        "web-and-protocols/http",
        "HTTP",
        "HTTP/1.1, HTTP/2, HTTP/3, REST, semantics.",
        (
            "You are an HTTP protocol specialist. Answer with reference to "
            "the relevant RFCs (9110, 9111, 9112, 9113, 9114). Be precise "
            "about the differences between HTTP/1.1, HTTP/2, and HTTP/3."
        ),
        (
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
        (
            "What protocol does HTTP/3 run on?",
            "What is HTTP/2 server push and why was it deprecated?",
            "What's the difference between PUT and PATCH?",
            "How do HTTP cookies work cross-origin?",
            "When does a server return 401 vs 403?",
            "What does Cache-Control: immutable mean?",
            "How does HSTS preload work?",
        ),
    ),
    (
        "web-and-protocols/tls",
        "TLS & Crypto",
        "TLS, certificates, public-key crypto.",
        "",
        (),
        (),
    ),
    # Data & ML
    (
        "data-and-ml",
        "Data & ML",
        "Data engineering, machine learning, AI systems.",
        "",
        (),
        (),
    ),
    ("data-and-ml/databases", "Databases", "SQL and NoSQL data stores.", "", (), ()),
    (
        "data-and-ml/machine-learning",
        "Machine Learning",
        "Models, training, evaluation.",
        "",
        (),
        (),
    ),
    # Science
    ("science", "Science", "Natural sciences.", "", (), ()),
    ("science/biology", "Biology", "Living systems, evolution, ecology.", "", (), ()),
    (
        "science/chemistry",
        "Chemistry",
        "Molecular composition and reactions.",
        "",
        (),
        (),
    ),
    (
        "science/physics",
        "Physics",
        "Matter, energy, and their interactions.",
        "",
        (),
        (),
    ),
    # Mathematics
    ("mathematics", "Mathematics", "Pure and applied math, statistics.", "", (), ()),
    # Humanities
    (
        "humanities",
        "Humanities",
        "History, philosophy, languages, literature.",
        "",
        (),
        (),
    ),
    ("humanities/history", "History", "Historical events and analysis.", "", (), ()),
    (
        "humanities/linguistics",
        "Linguistics",
        "Language structure and use.",
        "",
        (),
        (),
    ),
    # Health (note: medical advice has its own regulatory load — see PRODUCT.md §10)
    ("health", "Health", "General health knowledge. NOT medical advice.", "", (), ()),
    # Crafts & how-to
    (
        "crafts-and-how-to",
        "Crafts & How-to",
        "Practical skills, recipes, instructions.",
        "",
        (),
        (),
    ),
    (
        "crafts-and-how-to/cooking",
        "Cooking",
        "Recipes, techniques, food science.",
        "",
        (),
        (),
    ),
    # Law (general; jurisdiction-specific via tags)
    ("law", "Law", "Legal concepts. NOT legal advice.", "", (), ()),
    # Finance & economics
    (
        "finance-and-economics",
        "Finance & Economics",
        "Personal finance, markets, economics.",
        "",
        (),
        (),
    ),
)


def build_seed_categories() -> list[Category]:
    """Construct the seed Category list, including persona metadata on
    the routable leaves."""
    out: list[Category] = []
    for (
        category_id,
        display_name,
        description,
        system_prompt,
        specialty_tags,
        example_questions,
    ) in _SEED_TREE:
        if "/" in category_id:
            parent_id = category_id.rsplit("/", 1)[0]
        else:
            parent_id = None
        out.append(
            Category(
                category_id=category_id,
                parent_id=parent_id,
                display_name=display_name,
                description=description,
                system_prompt=system_prompt,
                specialty_tags=specialty_tags,
                example_questions=example_questions,
            )
        )
    return out


SEED_CATEGORIES: tuple[Category, ...] = tuple(build_seed_categories())


def populate(store: CategoryStore) -> int:
    """Insert seed categories into the store."""
    for c in SEED_CATEGORIES:
        store.add(c)
    return len(SEED_CATEGORIES)


# Legacy expert-id → category_id mapping. Kept so intake / migration
# code that still receives an expert-id string can resolve it to the
# category. New code should pass category ids directly.
EXPERT_DEFAULT_CATEGORY: Final[dict[str, str]] = {
    "python-typing": "programming/python/typing",
    "python-async": "programming/python/async",
    "python-packaging": "programming/python/packaging",
    "rust-ownership": "programming/rust/ownership",
    "http-protocol": "web-and-protocols/http",
}
