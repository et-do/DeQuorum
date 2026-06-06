"""Contributions: signed factual claims that augment expert answers.

v0.2 changes: each contribution is one version in a lineage. A lineage is "the
same claim, over time" — edits create new versions in the same lineage; the
voting system promotes one version to current and supersedes the rest.

Citations point at lineage_ids by default (auto-follow current); they can pin
to a specific version with `lineage:<id>@v<n>` for academic-style audit trails.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from dequorum.core.hashing import canonical_bytes, digest
from dequorum.core.node import Signature

# Sentinel for legacy / not-yet-categorized contributions. Mirrors the
# taxonomy module's constant of the same name so contribution code doesn't
# need to import the taxonomy module just for this.
UNCATEGORIZED_ID: Final[str] = "uncategorized"


@dataclass(frozen=True, slots=True)
class Contribution:
    """One version of a signed factual claim.

    The `contribution_id` is the content-hash of THIS version (so each version
    is unique even if text matches an older version). The `lineage_id` is
    stable across all versions of the same claim.
    """

    contribution_id: str
    lineage_id: str
    version_number: int
    parent_version: int | None
    contributor_id: str
    primary_category_id: str
    text: str
    citations: tuple[str, ...]
    signature: Signature

    @classmethod
    def create(
        cls,
        *,
        contributor_id: str,
        text: str,
        citations: tuple[str, ...],
        signing_key: bytes,
        primary_category_id: str = UNCATEGORIZED_ID,
        lineage_id: str | None = None,
        version_number: int = 1,
        parent_version: int | None = None,
    ) -> Contribution:
        """Construct and sign a Contribution.

        For a brand-new claim, omit `lineage_id` (one will be derived from content).
        For an update to an existing claim, pass the existing `lineage_id`, the new
        `version_number`, and the `parent_version` you're branching from.
        """
        # Derive lineage_id from content if not provided. Two contributors writing
        # identical text in the same category collide into the same lineage —
        # that's intentional, it makes accidental duplicates obvious.
        if lineage_id is None:
            lineage_id = (
                "lin:"
                + digest(
                    canonical_bytes({"text": text, "category": primary_category_id})
                )[:16]
            )

        payload = {
            "contributor_id": contributor_id,
            "primary_category_id": primary_category_id,
            "text": text,
            "citations": list(citations),
            "lineage_id": lineage_id,
            "version_number": version_number,
            "parent_version": parent_version,
        }
        contribution_id = digest(canonical_bytes(payload))
        sig = Signature.sign(
            node_id=contributor_id,
            signing_key=signing_key,
            payload=payload,
            result=contribution_id,
        )
        return cls(
            contribution_id=contribution_id,
            lineage_id=lineage_id,
            version_number=version_number,
            parent_version=parent_version,
            contributor_id=contributor_id,
            primary_category_id=primary_category_id,
            text=text,
            citations=citations,
            signature=sig,
        )

    def update(
        self,
        *,
        text: str | None = None,
        citations: tuple[str, ...] | None = None,
        primary_category_id: str | None = None,
        signing_key: bytes,
    ) -> Contribution:
        """Produce the next version in this lineage.

        Same contributor + same lineage, but new text/citations/category and
        an incremented version number. The new contribution starts as pending
        (status is tracked in the store, not on the dataclass).
        """
        return Contribution.create(
            contributor_id=self.contributor_id,
            primary_category_id=primary_category_id or self.primary_category_id,
            text=text if text is not None else self.text,
            citations=citations if citations is not None else self.citations,
            signing_key=signing_key,
            lineage_id=self.lineage_id,
            version_number=self.version_number + 1,
            parent_version=self.version_number,
        )
