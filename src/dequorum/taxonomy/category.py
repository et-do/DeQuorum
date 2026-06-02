"""Category: a node in the curated taxonomy tree."""

from __future__ import annotations

import re
from dataclasses import dataclass

_NON_SLUG = re.compile(r"[^a-z0-9-]+")
_MULTI_DASH = re.compile(r"-+")


def slugify(text: str) -> str:
    """Lowercase, hyphenate, strip non-slug chars. Used for category ids."""
    s = text.lower().replace("&", "and").replace("/", "-").strip()
    s = _NON_SLUG.sub("-", s)
    s = _MULTI_DASH.sub("-", s).strip("-")
    return s


@dataclass(frozen=True, slots=True)
class Category:
    """A node in the curated taxonomy tree.

    The id is a slash-joined slug path: "programming/python/typing".
    """

    category_id: str  # path slug: "programming/python/typing"
    parent_id: str | None
    display_name: str
    description: str = ""

    @property
    def slug(self) -> str:
        """The leaf slug of this category."""
        return self.category_id.rsplit("/", 1)[-1]

    @property
    def depth(self) -> int:
        """0 for top-level, 1 for sub, 2 for sub-sub."""
        return self.category_id.count("/")

    @property
    def ancestors(self) -> tuple[str, ...]:
        """Category ids of every ancestor, root first. Empty for top-level."""
        parts = self.category_id.split("/")
        return tuple("/".join(parts[: i + 1]) for i in range(len(parts) - 1))
