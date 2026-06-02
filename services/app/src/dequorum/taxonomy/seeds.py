"""Seed category taxonomy for v0.1.

The curated taxonomy is intentionally small at launch. Per contributor-intake.md §4,
new top-level categories are added via Tier 3 reviewer vote; this seed tree is just
what we ship pre-populated so the network has a starting structure to grow from.
"""

from __future__ import annotations

from typing import Final

from dequorum.taxonomy.category import Category
from dequorum.taxonomy.store import CategoryStore

# Sentinel for legacy / not-yet-categorized contributions.
UNCATEGORIZED_ID: Final[str] = "uncategorized"


# Each tuple is (category_id, display_name, description).
# Parent is derived from the slash structure of category_id.
_SEED_TREE: tuple[tuple[str, str, str], ...] = (
    # Sentinel
    (UNCATEGORIZED_ID, "Uncategorized", "Legacy or unassigned contributions."),
    # Programming
    (
        "programming",
        "Programming",
        "Software development across all languages and platforms.",
    ),
    ("programming/python", "Python", "The Python language and standard library."),
    (
        "programming/python/typing",
        "Python — Typing",
        "PEPs 484, 526, 612, 695; mypy; pyright.",
    ),
    (
        "programming/python/async",
        "Python — Async",
        "asyncio, trio, anyio, coroutines, event loop.",
    ),
    (
        "programming/python/packaging",
        "Python — Packaging",
        "pip, uv, pyproject.toml, wheels.",
    ),
    ("programming/rust", "Rust", "The Rust language and core ecosystem."),
    (
        "programming/rust/ownership",
        "Rust — Ownership",
        "Borrow checker, lifetimes, move semantics.",
    ),
    (
        "programming/javascript",
        "JavaScript",
        "JS / TypeScript / Node / browser runtime.",
    ),
    ("programming/go", "Go", "The Go language and runtime."),
    # Web & protocols
    (
        "web-and-protocols",
        "Web & Protocols",
        "Network protocols, web standards, formats.",
    ),
    ("web-and-protocols/http", "HTTP", "HTTP/1.1, HTTP/2, HTTP/3, REST, semantics."),
    ("web-and-protocols/tls", "TLS & Crypto", "TLS, certificates, public-key crypto."),
    # Data & ML
    ("data-and-ml", "Data & ML", "Data engineering, machine learning, AI systems."),
    ("data-and-ml/databases", "Databases", "SQL and NoSQL data stores."),
    (
        "data-and-ml/machine-learning",
        "Machine Learning",
        "Models, training, evaluation.",
    ),
    # Science
    ("science", "Science", "Natural sciences."),
    ("science/biology", "Biology", "Living systems, evolution, ecology."),
    ("science/chemistry", "Chemistry", "Molecular composition and reactions."),
    ("science/physics", "Physics", "Matter, energy, and their interactions."),
    # Mathematics
    ("mathematics", "Mathematics", "Pure and applied math, statistics."),
    # Humanities
    ("humanities", "Humanities", "History, philosophy, languages, literature."),
    ("humanities/history", "History", "Historical events and analysis."),
    ("humanities/linguistics", "Linguistics", "Language structure and use."),
    # Health (note: medical advice has its own regulatory load — see PRODUCT.md §10)
    ("health", "Health", "General health knowledge. NOT medical advice."),
    # Crafts & how-to
    (
        "crafts-and-how-to",
        "Crafts & How-to",
        "Practical skills, recipes, instructions.",
    ),
    ("crafts-and-how-to/cooking", "Cooking", "Recipes, techniques, food science."),
    # Law (general; jurisdiction-specific via tags)
    ("law", "Law", "Legal concepts. NOT legal advice."),
    # Finance & economics
    (
        "finance-and-economics",
        "Finance & Economics",
        "Personal finance, markets, economics.",
    ),
)


def build_seed_categories() -> list[Category]:
    """Construct the seed Category list with parent_ids derived from the slash hierarchy."""
    out: list[Category] = []
    for category_id, display_name, description in _SEED_TREE:
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
            )
        )
    return out


SEED_CATEGORIES: tuple[Category, ...] = tuple(build_seed_categories())


def populate(store: CategoryStore) -> int:
    """Insert seed categories into the store."""
    for c in SEED_CATEGORIES:
        store.add(c)
    return len(SEED_CATEGORIES)


# Map seed-expert slugs to their default category id.
EXPERT_DEFAULT_CATEGORY: Final[dict[str, str]] = {
    "python-typing": "programming/python/typing",
    "python-async": "programming/python/async",
    "python-packaging": "programming/python/packaging",
    "rust-ownership": "programming/rust/ownership",
    "http-protocol": "web-and-protocols/http",
}
