from __future__ import annotations

from dequorum.taxonomy.category import Category, slugify
from dequorum.taxonomy.seeds import (
    EXPERT_DEFAULT_CATEGORY,
    SEED_CATEGORIES,
    UNCATEGORIZED_ID,
    populate,
)
from dequorum.taxonomy.store import CategoryStore


def test_slugify_basic() -> None:
    assert slugify("Programming") == "programming"
    assert slugify("Web & Protocols") == "web-and-protocols"
    assert slugify("Crafts / How-To") == "crafts-how-to"


def test_category_depth_and_ancestors() -> None:
    cat = Category(
        category_id="programming/python/typing",
        parent_id="programming/python",
        display_name="Python — Typing",
    )
    assert cat.depth == 2
    assert cat.ancestors == ("programming", "programming/python")
    assert cat.slug == "typing"


def test_top_level_category_has_no_ancestors() -> None:
    cat = Category(category_id="science", parent_id=None, display_name="Science")
    assert cat.depth == 0
    assert cat.ancestors == ()


def test_store_seed_population() -> None:
    store = CategoryStore()
    n = populate(store)
    assert n == len(SEED_CATEGORIES)
    assert len(store) == n


def test_store_get_and_contains() -> None:
    store = CategoryStore()
    populate(store)
    cat = store.get("programming/python/typing")
    assert cat is not None
    assert cat.display_name == "Python — Typing"
    assert "programming/python/typing" in store
    assert "nonexistent" not in store


def test_store_children_of_root_lists_top_level() -> None:
    store = CategoryStore()
    populate(store)
    children = store.children_of(None)
    ids = {c.category_id for c in children}
    assert "programming" in ids
    assert "science" in ids
    # All have parent_id None
    for c in children:
        assert c.parent_id is None


def test_store_children_of_subcategory() -> None:
    store = CategoryStore()
    populate(store)
    children = store.children_of("programming/python")
    ids = {c.category_id for c in children}
    assert "programming/python/typing" in ids
    assert "programming/python/async" in ids


def test_uncategorized_sentinel_exists_in_seed() -> None:
    store = CategoryStore()
    populate(store)
    assert UNCATEGORIZED_ID in store


def test_expert_default_category_points_at_seeded_categories() -> None:
    store = CategoryStore()
    populate(store)
    for expert_id, cat_id in EXPERT_DEFAULT_CATEGORY.items():
        assert cat_id in store, (
            f"expert {expert_id} maps to category {cat_id} which isn't in the seed taxonomy"
        )
