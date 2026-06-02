"""Submission pipeline: runs all quality gates and produces a signed Contribution.

Gates applied in order:
1. Schema validation (length, citation requirement, https-only URLs, category exists)
2. Duplicate detection (similarity surface, doesn't block unless `block_on_likely=True`)
3. Sign + persist as pending

The submission pipeline DOES NOT enforce the contributor tier daily cap — that
belongs to a rate-limiter middleware (rate-limiting requires wall-clock time
which the dataclasses-and-store layer deliberately avoids).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse

from dequorum.core.errors import CompositionError
from dequorum.identity.contributor import Contributor
from dequorum.intake.dedup import (
    DuplicateBand,
    DuplicateDetector,
    DuplicateReport,
)
from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.status import STATUS_PENDING
from dequorum.knowledge.store import ContributionStore
from dequorum.taxonomy.store import CategoryStore

MIN_CLAIM_LENGTH: Final[int] = 50
MAX_CLAIM_LENGTH: Final[int] = 1500


class SubmissionError(CompositionError):
    """Hard-fail: a gate rejected the submission outright."""


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    contribution: Contribution
    duplicate_report: DuplicateReport


class SubmissionPipeline:
    """Composes schema validation, duplicate detection, signing, and persistence."""

    def __init__(
        self,
        contribution_store: ContributionStore,
        category_store: CategoryStore,
        duplicate_detector: DuplicateDetector | None = None,
        *,
        block_on_likely_duplicate: bool = False,
    ) -> None:
        self._contribution_store = contribution_store
        self._category_store = category_store
        self._duplicate_detector = duplicate_detector
        self._block_on_likely = block_on_likely_duplicate

    def submit(
        self,
        *,
        contributor: Contributor,
        contributor_signing_key: bytes,
        expert_id: str,
        text: str,
        citations: tuple[str, ...],
        primary_category_id: str,
        update_lineage_id: str | None = None,
    ) -> SubmissionResult:
        """Submit a new claim or an updated version of an existing claim.

        - For a new claim, omit `update_lineage_id`.
        - For an update, pass the existing `lineage_id`. The pipeline looks up
          the current contribution and produces a `version_number = current + 1`
          contribution branching from the current version.
        """
        self._validate_schema(text, citations)
        self._validate_category(primary_category_id)

        # Duplicate detection only matters for brand-new submissions; updates
        # are explicit version bumps of an existing lineage.
        if update_lineage_id is None and self._duplicate_detector is not None:
            report = self._duplicate_detector.check(
                text, category_id=primary_category_id
            )
            if self._block_on_likely and report.has_likely_duplicate:
                raise SubmissionError(
                    f"Likely duplicate of existing claim: {report.suggested_action}"
                )
        else:
            report = DuplicateReport(band=DuplicateBand.CLEAR, top_candidates=())

        if update_lineage_id is not None:
            contribution = self._build_update(
                lineage_id=update_lineage_id,
                contributor=contributor,
                contributor_signing_key=contributor_signing_key,
                text=text,
                citations=citations,
                primary_category_id=primary_category_id,
                expert_id=expert_id,
            )
        else:
            contribution = Contribution.create(
                expert_id=expert_id,
                contributor_id=contributor.contributor_id,
                primary_category_id=primary_category_id,
                text=text,
                citations=citations,
                signing_key=contributor_signing_key,
            )

        self._contribution_store.add(contribution, status=STATUS_PENDING)
        return SubmissionResult(contribution=contribution, duplicate_report=report)

    def _build_update(
        self,
        *,
        lineage_id: str,
        contributor: Contributor,
        contributor_signing_key: bytes,
        text: str,
        citations: tuple[str, ...],
        primary_category_id: str,
        expert_id: str,
    ) -> Contribution:
        # Use the highest existing version (current or not) as the parent.
        # This handles the case where the current is approved and an in-flight
        # pending edit already exists.
        latest = self._contribution_store.latest_version_for_lineage(lineage_id)
        if latest == 0:
            raise SubmissionError(f"unknown lineage: {lineage_id!r}")
        return Contribution.create(
            expert_id=expert_id,
            contributor_id=contributor.contributor_id,
            primary_category_id=primary_category_id,
            text=text,
            citations=citations,
            signing_key=contributor_signing_key,
            lineage_id=lineage_id,
            version_number=latest + 1,
            parent_version=latest,
        )

    # --- gates ---

    def _validate_schema(self, text: str, citations: tuple[str, ...]) -> None:
        text = text.strip()
        if len(text) < MIN_CLAIM_LENGTH:
            raise SubmissionError(
                f"claim too short: {len(text)} chars (min {MIN_CLAIM_LENGTH})"
            )
        if len(text) > MAX_CLAIM_LENGTH:
            raise SubmissionError(
                f"claim too long: {len(text)} chars (max {MAX_CLAIM_LENGTH})"
            )
        if not citations:
            raise SubmissionError("at least one citation URL is required")
        for url in citations:
            parsed = urlparse(url)
            if parsed.scheme != "https":
                raise SubmissionError(f"citation must be https: {url!r}")
            if not parsed.netloc:
                raise SubmissionError(f"citation URL has no host: {url!r}")

    def _validate_category(self, category_id: str) -> None:
        if category_id not in self._category_store:
            raise SubmissionError(f"unknown category: {category_id!r}")
