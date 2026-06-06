"""Category: a node in the curated taxonomy tree.

As of 0.2 the Category carries persona metadata (system prompt,
specialty tags, example questions) that used to live on the now-
deleted Expert layer. A Category is "routable" iff it has a non-empty
`system_prompt` — non-routable categories exist only as organizational
parents in the tree, and queries can't be routed to them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

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
    Persona fields default to empty: most internal-node categories
    aren't routable, only leaves with a curated persona are.
    """

    category_id: str
    parent_id: str | None
    display_name: str
    description: str = ""
    system_prompt: str = ""
    specialty_tags: tuple[str, ...] = field(default_factory=tuple)
    example_questions: tuple[str, ...] = field(default_factory=tuple)

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

    @property
    def is_routable(self) -> bool:
        """True iff this category has a persona, i.e. can be the target of
        the router. Non-routable categories are organizational only."""
        return bool(self.system_prompt.strip())
