"""FastAPI app factory: JSON-only API at /v1/*.

The frontend lives in services/frontend (React + Vite). This service emits
no HTML — every route returns JSON. The Caddy reverse proxy strips `/api`
before forwarding, so external URLs are `/api/v1/...` while FastAPI sees
`/v1/...`.

Real-time review queue updates are delivered via Server-Sent Events at
`/v1/review/stream`; clients use the browser-native `EventSource` API or
TanStack Query's streaming integrations.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field

from fastapi import Body, Depends, FastAPI, HTTPException, Path, Query
from fastapi.responses import Response, StreamingResponse

from dequorum.auth import AuthenticatedUser, init_firebase, require_user
from dequorum.chat.store import DEFAULT_TITLE, ROLE_NETWORK, ROLE_USER
from dequorum.comments.comment import Comment, LineAnchor
from dequorum.core.errors import CompositionError
from dequorum.db import (
    DEFAULT_DATABASE_URL,
    close_pool,
    init_pool,
    open_category_store,
    open_chat_store,
    open_comment_store,
    open_contribution_store,
    open_identity_store,
)
from dequorum.db.migrate import upgrade_to_head
from dequorum.identity.agreement import current_agreement
from dequorum.identity.contributor import Tier
from dequorum.identity.seeds import commenter_for_uid, commenter_record_for_uid
from dequorum.identity.seeds import populate as populate_seed_contributors
from dequorum.inference.base_model import BaseModel
from dequorum.inference.pipeline import _augment_system_prompt
from dequorum.inference.provider import build_serving_model
from dequorum.intake import DuplicateDetector, SubmissionPipeline
from dequorum.knowledge.seeds import populate as populate_seed_contributions
from dequorum.knowledge.store import (
    STATUS_PENDING,
    VALID_STATUSES,
)
from dequorum.retrieval import Retriever
from dequorum.review.service import (
    APPROVAL_THRESHOLD,
    REJECTION_THRESHOLD,
    ReviewService,
)
from dequorum.routing import EmbeddingRouter, KeywordRouter
from dequorum.routing.embedder import SentenceTransformerEmbedder
from dequorum.taxonomy.category import Category
from dequorum.taxonomy.seeds import populate as populate_seed_categories


@dataclass
class AppConfig:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DEQUORUM_DATABASE_URL", DEFAULT_DATABASE_URL
        )
    )
    use_mock: bool = False
    # DEQUORUM_OLLAMA_MODEL lets an environment pin a specific tag/id
    # (e.g. compose sets the snappier 3B for local CPU dev); empty falls
    # back to DEFAULT_BASE_MODEL_ID from inference/models.py.
    ollama_model: str = field(
        default_factory=lambda: os.environ.get("DEQUORUM_OLLAMA_MODEL", "")
    )
    # Honor DEQUORUM_OLLAMA_HOST so compose's "http://ollama:11434" reaches
    # the app. Falls back to localhost for standalone `dequorum serve`.
    ollama_host: str = field(
        default_factory=lambda: os.environ.get(
            "DEQUORUM_OLLAMA_HOST", "http://localhost:11434"
        )
    )
    # Serving model provider: "ollama" (default; free self-hosted) or "openai"
    # (any OpenAI-compatible hosted endpoint — Groq/DeepInfra/Together/…). Dev and
    # tests stay on ollama/mock at $0; production opts into a fast hosted open model.
    # See docs/architecture/model-serving.md.
    model_provider: str = field(
        default_factory=lambda: os.environ.get("DEQUORUM_MODEL_PROVIDER", "ollama")
    )
    # For the openai provider: endpoint, key, and model tag at that provider.
    model_base_url: str = field(
        default_factory=lambda: os.environ.get("DEQUORUM_MODEL_BASE_URL", "")
    )
    model_api_key: str = field(
        default_factory=lambda: os.environ.get("DEQUORUM_MODEL_API_KEY", "")
    )
    model: str = field(default_factory=lambda: os.environ.get("DEQUORUM_MODEL", ""))
    top_k: int = 2
    retrieve_top_k: int = 3
    router: str = "embedding"
    min_score: float | None = None
    composition: str = "pick_best"
    extras: dict = field(default_factory=dict)


_config = AppConfig()


def configure_app(
    *,
    database_url: str | None = None,
    use_mock: bool | None = None,
    ollama_model: str | None = None,
    ollama_host: str | None = None,
    top_k: int | None = None,
    retrieve_top_k: int | None = None,
    router: str | None = None,
    min_score: float | None = None,
    composition: str | None = None,
) -> AppConfig:
    """Mutate the module-level config before create_app(). CLI calls this first."""
    if database_url is not None:
        _config.database_url = database_url
    if use_mock is not None:
        _config.use_mock = use_mock
    if ollama_model is not None:
        _config.ollama_model = ollama_model
    if ollama_host is not None:
        _config.ollama_host = ollama_host
    if top_k is not None:
        _config.top_k = top_k
    if retrieve_top_k is not None:
        _config.retrieve_top_k = retrieve_top_k
    if router is not None:
        _config.router = router
    if min_score is not None:
        _config.min_score = min_score
    if composition is not None:
        _config.composition = composition
    return _config


# The sentence-transformers embedder is the expensive piece: model
# weights load on first .embed() call (~300-800ms). Cache the
# embedder at module scope so it loads exactly once per process.
# The router wrappers around it are cheap to reconstruct.
_cached_embedder: SentenceTransformerEmbedder | None = None


def _embedder() -> SentenceTransformerEmbedder:
    global _cached_embedder
    if _cached_embedder is None:
        _cached_embedder = SentenceTransformerEmbedder()
    return _cached_embedder


def _routable_categories() -> tuple[Category, ...]:
    """Load the universe of routable (persona-carrying) categories from
    the Postgres store. Used to build a router on demand. The result
    is small (5 at v0.1, low tens-to-hundreds at scale) and stable
    within a process; the embedder caches embeddings of the joined
    profile texts."""
    with open_category_store() as cs:
        return tuple(cs.routable())


def _build_router(
    categories: Sequence[Category] | None = None,
) -> EmbeddingRouter | KeywordRouter:
    cats = categories if categories is not None else _routable_categories()
    if _config.router == "embedding":
        # 0.30 is data-driven: the threshold sweep in
        # docs/benchmarks/routebench.md shows it eliminates the
        # MMLU-shaped OOD false-positives (19% leak at 0.18) while
        # keeping 100% accept on in-domain at N=127.
        threshold = 0.30 if _config.min_score is None else _config.min_score
        fallback = KeywordRouter(cats, fallback_to_all=False, min_score=1.0)
        return EmbeddingRouter(
            cats, _embedder(), min_score=threshold, fallback=fallback
        )
    threshold = 1.0 if _config.min_score is None else _config.min_score
    return KeywordRouter(cats, min_score=threshold)


# Short / chatty inputs almost never benefit from expert routing —
# the embedding similarity collapses to noise on 1-3 token strings.
# Bypass routing for these and let the base assistant handle them
# directly, saving 80-300ms of embed time per casual message.
_SMALL_TALK = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "yo",
        "sup",
        "thanks",
        "thank you",
        "ok",
        "okay",
        "cool",
        "nice",
        "lol",
        "haha",
        "bye",
        "goodbye",
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
    }
)


def _is_trivial_query(text: str) -> bool:
    t = text.strip().lower().rstrip(".!?,;:")
    if len(t) < 4:
        return True
    if t in _SMALL_TALK:
        return True
    # Multi-word greetings / acks that start with a small-talk prefix.
    if len(t.split()) <= 4:
        for prefix in (
            "hi ",
            "hello ",
            "hey ",
            "thanks ",
            "thank ",
            "good morning",
            "good evening",
        ):
            if t.startswith(prefix):
                return True
    return False


def _model() -> BaseModel:
    return build_serving_model(
        use_mock=_config.use_mock,
        provider=_config.model_provider,
        # ollama provider keeps the existing DEQUORUM_OLLAMA_MODEL pin; the openai
        # provider uses DEQUORUM_MODEL (the tag at the hosted endpoint).
        model=_config.model or _config.ollama_model,
        host=_config.ollama_host,
        base_url=_config.model_base_url,
        api_key=_config.model_api_key,
    )


def _seed_if_empty() -> None:
    """Populate seed data on startup.

    - Identity + contributions are seeded only on an empty DB so we
      don't clobber whatever the running instance has accumulated.
    - The category taxonomy is a *curated, code-owned* artifact — its
      shape is part of the build, not user data. We re-upsert it on
      every startup so schema migrations that add columns (e.g.
      0004 adding `system_prompt` for the persona-on-category model)
      get the new fields populated on existing rows without an extra
      manual step. `CategoryStore.add` is `ON CONFLICT DO UPDATE`, so
      this is cheap and self-healing.
    """
    with open_identity_store() as istore:
        istore.ensure_seed_agreements()
        if len(istore) == 0:
            populate_seed_contributors(istore)
    with open_contribution_store() as cstore:
        if len(cstore) == 0:
            populate_seed_contributions(cstore)
    with open_category_store() as cat_store:
        populate_seed_categories(cat_store)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_pool(_config.database_url)
    upgrade_to_head(_config.database_url)
    _seed_if_empty()
    init_firebase()

    # Pre-warm in the background so the first real request doesn't
    # pay the embedder load (~300-800ms) or Ollama model-load
    # (~2-8s) cost. Both are best-effort — failures are swallowed.
    async def _prewarm() -> None:
        def _warm_router() -> None:
            try:
                router = _build_router()
                router.route("warmup", top_k=1)
            except Exception:
                pass

        def _warm_model() -> None:
            try:
                _model().complete(system="ping", user="ping")
            except Exception:
                pass

        await asyncio.gather(
            asyncio.to_thread(_warm_router),
            asyncio.to_thread(_warm_model),
        )

    # Hold a reference so the task isn't garbage-collected mid-flight
    # (the task is fire-and-forget but Python's loop only keeps weak refs).
    _prewarm_task = asyncio.create_task(_prewarm())
    _prewarm_task.add_done_callback(lambda t: t.exception())

    try:
        yield
    finally:
        close_pool()


# --- serialization helpers ------------------------------------------------


def _serialize_contribution(c: object, status: str | None, tally: int) -> dict:
    return {
        "contribution_id": c.contribution_id,  # type: ignore[attr-defined]
        "lineage_id": c.lineage_id,  # type: ignore[attr-defined]
        "version_number": c.version_number,  # type: ignore[attr-defined]
        "parent_version": c.parent_version,  # type: ignore[attr-defined]
        "contributor_id": c.contributor_id,  # type: ignore[attr-defined]
        "primary_category_id": c.primary_category_id,  # type: ignore[attr-defined]
        "text": c.text,  # type: ignore[attr-defined]
        "citations": list(c.citations),  # type: ignore[attr-defined]
        "signature": asdict(c.signature),  # type: ignore[attr-defined]
        "status": status,
        "tally": tally,
    }


def _serialize_vote(v: object) -> dict:
    return {
        "vote_id": v.vote_id,  # type: ignore[attr-defined]
        "contribution_id": v.contribution_id,  # type: ignore[attr-defined]
        "voter_id": v.voter_id,  # type: ignore[attr-defined]
        "score": v.score,  # type: ignore[attr-defined]
        "signature": asdict(v.signature),  # type: ignore[attr-defined]
    }


def _serialize_contributor(c: object) -> dict:
    return {
        "contributor_id": c.contributor_id,  # type: ignore[attr-defined]
        "display_name": c.display_name,  # type: ignore[attr-defined]
        "public_key_hex": c.public_key.hex(),  # type: ignore[attr-defined]
        "tier": int(c.tier),  # type: ignore[attr-defined]
        "tier_name": c.tier.name,  # type: ignore[attr-defined]
        "agreement_version": c.agreement_version,  # type: ignore[attr-defined]
        "vote_weight": c.vote_weight,  # type: ignore[attr-defined]
        "daily_submission_cap": c.daily_submission_cap,  # type: ignore[attr-defined]
        "has_email": c.email_hash is not None,  # type: ignore[attr-defined]
        "created_at": c.created_at,  # type: ignore[attr-defined]
    }


def _commenter_id_for(user: AuthenticatedUser) -> str:
    """Map a Firebase uid to the contributor_id we use to sign comments
    by that user. Mirrors the seed-contributor derivation so the same
    uid always yields the same id."""
    contributor_id, _ = commenter_for_uid(user.uid, user.display_name)
    return contributor_id


def _is_curator(user: AuthenticatedUser) -> bool:
    """Whether this user has curator-tier moderation powers.

    DEV PLACEHOLDER: today, no Firebase users are mapped to the
    `Tier.CURATOR` ladder rung — the role only exists on seed
    contributors. Returning False here keeps redaction strictly to
    comment authors until the contributor-onboarding flow lands. The
    moderation path is wired and tested; flip this once we have a way
    to read the user's tier from the identity store.
    """
    return False


def _serialize_comment(c: Comment) -> dict:
    """Public-shape JSON for a Comment. Redacted comments expose the
    redaction metadata but hide the body — callers see a placeholder
    via `body` so threading stays renderable."""
    return {
        "comment_id": c.comment_id,
        "contribution_id": c.contribution_id,
        "parent_comment_id": c.parent_comment_id,
        "author_id": c.author_id,
        "body": c.display_body,
        "line_anchor": (
            {"start_line": c.line_anchor.start_line, "end_line": c.line_anchor.end_line}
            if c.line_anchor
            else None
        ),
        "created_at": c.created_at,
        "redacted_at": c.redacted_at,
        "redacted_by": c.redacted_by,
        "replaces_comment_id": c.replaces_comment_id,
        "signature": asdict(c.signature),
    }


def _serialize_category(cat: Category) -> dict:
    return {
        "category_id": cat.category_id,
        "parent_id": cat.parent_id,
        "display_name": cat.display_name,
        "depth": cat.depth,
        "description": cat.description,
        "is_routable": cat.is_routable,
        "specialty_tags": list(cat.specialty_tags),
        "example_questions": list(cat.example_questions),
    }


def create_app() -> FastAPI:
    app = FastAPI(
        title="dequorum",
        description="DeQuorum JSON API. UI is served by services/frontend (React).",
        version="0.1.0",
        lifespan=_lifespan,
    )

    # ---- health + meta ----

    @app.get("/v1/healthz", tags=["meta"])
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/v1/inference/diag", tags=["meta"])
    async def inference_diag() -> dict:
        """Inspect Ollama's view of the world so we can debug slow
        responses. Reports which models are currently loaded, the
        target tag from our config, and a TTFT timing for a
        minimal prompt. The biggest wins from this endpoint:

        - "size_vram == 0" on a loaded model means it fell back to
          CPU. On consumer hardware that turns a 1-second reply
          into a 10-minute one.
        - "ttft_ms" over ~1500ms with the model loaded points at
          either a context-window bloat or wrong device.
        """
        from urllib import error as _err
        from urllib import request as _req

        host = _config.ollama_host
        target_tag = _config.ollama_model or "(default from registry)"

        def _ps() -> dict:
            try:
                with _req.urlopen(f"{host}/api/ps", timeout=5) as resp:
                    return json.loads(resp.read().decode())
            except (_err.URLError, TimeoutError) as exc:
                return {"error": str(exc)}

        def _ttft() -> dict:
            t0 = time.perf_counter()
            first_chunk_ms: float | None = None
            chunks = 0
            total_chars = 0
            try:
                for piece in _model().stream(system="You are terse.", user="Say hi."):
                    if first_chunk_ms is None:
                        first_chunk_ms = (time.perf_counter() - t0) * 1000
                    chunks += 1
                    total_chars += len(piece)
                    if chunks >= 10:  # plenty to estimate throughput
                        break
            except Exception as exc:
                return {"error": str(exc)}
            total_ms = (time.perf_counter() - t0) * 1000
            return {
                "ttft_ms": round(first_chunk_ms or total_ms, 1),
                "total_ms": round(total_ms, 1),
                "chunks": chunks,
                "chars": total_chars,
                "chars_per_sec": round(total_chars / (total_ms / 1000), 1)
                if total_ms
                else 0,
            }

        ps, timing = await asyncio.gather(
            asyncio.to_thread(_ps),
            asyncio.to_thread(_ttft),
        )
        return {
            "ollama_host": host,
            "target_tag": target_tag,
            "ps": ps,
            "timing": timing,
            "use_mock": _config.use_mock,
        }

    @app.post("/v1/inference/warmup", tags=["meta"])
    async def warmup() -> dict:
        """Touch the base model with an empty prompt to force Ollama to
        load weights into VRAM. The client fires this when the chat
        route mounts so the first real message doesn't pay cold-start.
        Best-effort — failures are swallowed."""

        def _touch() -> str:
            try:
                # `complete` with an empty user msg sends a minimal
                # /api/chat call. With keep_alive set on the model
                # call, this leaves the model resident.
                return _model().complete(system="ping", user="ping")
            except Exception:
                return ""

        await asyncio.to_thread(_touch)
        return {"status": "ok"}

    @app.get("/v1/meta", tags=["meta"])
    def meta() -> dict:
        return {
            "database_url": _config.database_url,
            "ollama_host": _config.ollama_host,
            "use_mock": _config.use_mock,
            "approval_threshold": APPROVAL_THRESHOLD,
            "rejection_threshold": REJECTION_THRESHOLD,
            "valid_statuses": sorted(VALID_STATUSES),
        }

    # ---- contributions ----

    @app.get("/v1/contributions", tags=["contributions"])
    def list_contributions(
        status: str | None = Query(None),
        contributor: str | None = Query(None),
        category: str | None = Query(None),
        q: str | None = Query(
            None, description="Case-insensitive substring match against text"
        ),
    ) -> list[dict]:
        if status is not None and status not in VALID_STATUSES:
            raise HTTPException(400, f"invalid status: {status!r}")
        with open_contribution_store() as store:
            if contributor:
                contribs = store.list_by_contributor(contributor)
            elif category:
                contribs = store.list_by_category(category, status=status)
            elif status:
                contribs = store.list_by_status(status)
            else:
                contribs = list(iter(store))
            if q:
                needle = q.lower()
                contribs = [c for c in contribs if needle in c.text.lower()]
            return [
                _serialize_contribution(
                    c,
                    store.get_status(c.contribution_id),
                    store.vote_tally(c.contribution_id),
                )
                for c in contribs
            ]

    @app.get("/v1/contributions/{contribution_id}", tags=["contributions"])
    def get_contribution(contribution_id: str = Path(...)) -> dict:
        with open_contribution_store() as store:
            c = store.get(contribution_id)
            if c is None:
                raise HTTPException(404, "contribution not found")
            status = store.get_status(contribution_id)
            tally = store.vote_tally(contribution_id)
            votes = [_serialize_vote(v) for v in store.votes_for(contribution_id)]
        return {
            **_serialize_contribution(c, status, tally),
            "votes": votes,
        }

    @app.get("/v1/contributions/{contribution_id}/verify", tags=["contributions"])
    def verify_contribution(contribution_id: str = Path(...)) -> dict:
        """Publicly verify a contribution's signed attribution.

        Deliberately unauthenticated: the whole point of the proof chain is
        that *anyone* can confirm a claim's authorship and integrity using
        only public data. Two independent checks are reported:
          - content_intact: the stored text/metadata still hashes to the
            signed payload and contribution_id (storage hasn't been altered).
          - signature_valid: the Ed25519 signature verifies against the
            contributor's published public key (the holder of the private
            key authored exactly this).
        Neither requires any secret, so the result does not rest on trusting
        the operator.
        """
        with open_contribution_store() as store:
            c = store.get(contribution_id)
            if c is None:
                raise HTTPException(404, "contribution not found")
        with open_identity_store() as istore:
            contributor = istore.get(c.contributor_id)
        if contributor is None:
            return {
                "contribution_id": contribution_id,
                "contributor_id": c.contributor_id,
                "algorithm": "Ed25519",
                "content_intact": c.signature.covers(
                    payload=c.signed_payload(), result=c.contribution_id
                ),
                "signature_valid": False,
                "verified": False,
                "reason": "signer public key not on file",
            }
        public_key = contributor.public_key
        content_intact = c.signature.covers(
            payload=c.signed_payload(), result=c.contribution_id
        )
        signature_valid = c.signature.verify(public_key)
        return {
            "contribution_id": contribution_id,
            "contributor_id": c.contributor_id,
            "public_key_hex": public_key.hex(),
            "signature_hex": c.signature.digest,
            "algorithm": "Ed25519",
            "content_intact": content_intact,
            "signature_valid": signature_valid,
            "verified": content_intact and signature_valid,
        }

    @app.post("/v1/contributions", tags=["contributions"], status_code=201)
    def submit_contribution(
        payload: dict = Body(...),
        user: AuthenticatedUser = Depends(require_user),
    ) -> dict:
        category_id = (payload.get("primary_category_id") or "").strip()
        text = (payload.get("text") or "").strip()
        citations = tuple(c.strip() for c in payload.get("citations", []) if c.strip())
        if not category_id:
            raise HTTPException(400, "primary_category_id is required")
        if not text:
            raise HTTPException(400, "text is required")

        # Submitting contributor is the signed-in user. The helper
        # derives the same contributor_id the voting endpoint would,
        # so self-vote detection works without a registry lookup.
        contributor, signing_key = commenter_record_for_uid(user.uid, user.display_name)

        # Publish the contributor's public key (idempotent upsert) so their
        # contributions are independently verifiable via GET .../verify —
        # without a published key on file there is nothing to check a
        # signature against.
        with open_identity_store() as istore:
            istore.add(contributor)

        embedder = _embedder()
        with open_contribution_store() as store, open_category_store() as cat_store:
            pipeline = SubmissionPipeline(
                contribution_store=store,
                category_store=cat_store,
                duplicate_detector=DuplicateDetector(store, embedder),
            )
            try:
                result = pipeline.submit(
                    contributor=contributor,
                    contributor_signing_key=signing_key,
                    text=text,
                    citations=citations,
                    primary_category_id=category_id,
                )
            except CompositionError as exc:
                raise HTTPException(400, str(exc)) from exc
            c = result.contribution
            tally = store.vote_tally(c.contribution_id)
            status = store.get_status(c.contribution_id)
        return {
            **_serialize_contribution(c, status, tally),
            "duplicate_check": {
                "band": result.duplicate_report.band.value,
                "suggested_action": result.duplicate_report.suggested_action,
                "top_candidates": [
                    {
                        "contribution_id": cand.contribution_id,
                        "lineage_id": cand.lineage_id,
                        "score": round(cand.score, 4),
                        "text_preview": cand.text[:120],
                    }
                    for cand in result.duplicate_report.top_candidates
                ],
            },
        }

    @app.post(
        "/v1/contributions/{contribution_id}/votes",
        tags=["contributions"],
        status_code=201,
    )
    def cast_vote(
        contribution_id: str = Path(...),
        payload: dict = Body(...),
        user: AuthenticatedUser = Depends(require_user),
    ) -> dict:
        score = payload.get("score")
        if score not in (-1, 0, 1):
            raise HTTPException(400, "score must be -1, 0, or 1")
        voter_id, voter_key = commenter_for_uid(user.uid, user.display_name)
        with open_contribution_store() as store:
            service = ReviewService(store)
            try:
                outcome = service.cast_vote(
                    contribution_id=contribution_id,
                    voter_id=voter_id,
                    score=int(score),
                    signing_key=voter_key,
                )
            except CompositionError as exc:
                raise HTTPException(400, str(exc)) from exc
            tally = store.vote_tally(contribution_id)
            status = store.get_status(contribution_id)
        return {
            "outcome": asdict(outcome),
            "tally": tally,
            "status": status,
        }

    # ---- comments on contributions ----

    @app.get("/v1/contributions/{contribution_id}/comments", tags=["comments"])
    def list_contribution_comments(contribution_id: str = Path(...)) -> list[dict]:
        """Flat, time-ordered comment list. Thread shape is implicit in
        the `parent_comment_id` field; the client renders the tree."""
        with open_contribution_store() as cstore:
            if cstore.get(contribution_id) is None:
                raise HTTPException(404, "contribution not found")
        with open_comment_store() as comments:
            return [
                _serialize_comment(c)
                for c in comments.list_for_contribution(contribution_id)
            ]

    @app.post(
        "/v1/contributions/{contribution_id}/comments",
        tags=["comments"],
        status_code=201,
    )
    def create_contribution_comment(
        contribution_id: str = Path(...),
        payload: dict = Body(...),
        user: AuthenticatedUser = Depends(require_user),
    ) -> dict:
        """Post a new comment on a contribution.

        Body schema:
            body                str    required, non-empty
            parent_comment_id   str?   optional, threads under that comment
            line_anchor         object? optional, {start_line, end_line}
            replaces_comment_id str?   optional, original this comment supersedes
        """
        body_text = (payload.get("body") or "").strip()
        if not body_text:
            raise HTTPException(400, "body is required")
        if len(body_text) > 10_000:
            raise HTTPException(400, "body must be 10,000 characters or fewer")
        parent_id = payload.get("parent_comment_id") or None
        replaces_id = payload.get("replaces_comment_id") or None
        anchor_payload = payload.get("line_anchor")
        anchor: LineAnchor | None = None
        if anchor_payload:
            try:
                anchor = LineAnchor(
                    start_line=int(anchor_payload["start_line"]),
                    end_line=int(anchor_payload["end_line"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise HTTPException(400, f"invalid line_anchor: {exc}") from exc

        with open_contribution_store() as cstore:
            target = cstore.get(contribution_id)
            if target is None:
                raise HTTPException(404, "contribution not found")

        with open_comment_store() as comments:
            if parent_id is not None:
                parent = comments.get(parent_id)
                if parent is None:
                    raise HTTPException(400, "parent_comment_id not found")
                if parent.contribution_id != contribution_id:
                    raise HTTPException(
                        400, "parent_comment_id belongs to a different contribution"
                    )
            if replaces_id is not None:
                original = comments.get(replaces_id)
                if original is None:
                    raise HTTPException(400, "replaces_comment_id not found")
                if original.author_id != _commenter_id_for(user):
                    raise HTTPException(
                        403, "only the original author can replace their own comment"
                    )

            contributor_id, signing_key = commenter_for_uid(user.uid, user.display_name)
            comment = Comment.create(
                contribution_id=contribution_id,
                author_id=contributor_id,
                body=body_text,
                signing_key=signing_key,
                parent_comment_id=parent_id,
                line_anchor=anchor,
                replaces_comment_id=replaces_id,
                created_at=int(time.time()),
            )
            comments.add(comment)
        return _serialize_comment(comment)

    @app.delete(
        "/v1/comments/{comment_id}",
        tags=["comments"],
        status_code=204,
    )
    def redact_comment(
        comment_id: str = Path(...),
        user: AuthenticatedUser = Depends(require_user),
    ) -> Response:
        """Soft-delete (redact) a comment.

        Allowed for: the original author, or a `Tier.CURATOR` (tier 4)
        moderator. The row stays — the body is just hidden in future
        responses, preserving thread structure and the proof chain.
        """
        with open_comment_store() as comments:
            existing = comments.get(comment_id)
            if existing is None:
                raise HTTPException(404, "comment not found")
            requester_id = _commenter_id_for(user)
            is_author = existing.author_id == requester_id
            is_curator = _is_curator(user)
            if not (is_author or is_curator):
                raise HTTPException(
                    403, "only the author or a curator may redact a comment"
                )
            comments.redact(
                comment_id,
                redacted_by=requester_id,
                redacted_at=int(time.time()),
            )
        return Response(status_code=204)

    # ---- review queue ----

    @app.get("/v1/review", tags=["review"])
    def review_queue() -> list[dict]:
        with open_contribution_store() as store:
            contribs = store.list_by_status(STATUS_PENDING)
            return [
                {
                    **_serialize_contribution(
                        c,
                        STATUS_PENDING,
                        store.vote_tally(c.contribution_id),
                    ),
                    "votes": [
                        _serialize_vote(v) for v in store.votes_for(c.contribution_id)
                    ],
                }
                for c in contribs
            ]

    @app.get("/v1/review/stream", tags=["review"])
    async def review_stream() -> StreamingResponse:
        """Server-Sent Events: emits the current queue every 2s.

        Clients open this once and receive a stream of `data: <json>\\n\\n`
        frames. Polling-via-stream is simpler than a real pub/sub and fits
        the dev scale; swap for Redis pubsub when load demands it.
        """

        async def gen() -> AsyncIterator[bytes]:
            previous: str | None = None
            while True:
                with open_contribution_store() as store:
                    contribs = store.list_by_status(STATUS_PENDING)
                    payload = [
                        {
                            **_serialize_contribution(
                                c,
                                STATUS_PENDING,
                                store.vote_tally(c.contribution_id),
                            ),
                            "votes": [
                                _serialize_vote(v)
                                for v in store.votes_for(c.contribution_id)
                            ],
                        }
                        for c in contribs
                    ]
                payload_str = json.dumps(payload)
                if payload_str != previous:
                    yield f"data: {payload_str}\n\n".encode()
                    previous = payload_str
                await asyncio.sleep(2)

        return StreamingResponse(gen(), media_type="text/event-stream")

    # ---- contributors / onboarding ----

    @app.get("/v1/contributors", tags=["contributors"])
    def list_contributors() -> list[dict]:
        with open_identity_store() as store:
            return [_serialize_contributor(c) for c in store.list_all()]

    @app.get("/v1/contributors/{contributor_id}", tags=["contributors"])
    def get_contributor(contributor_id: str = Path(...)) -> dict:
        with open_identity_store() as store:
            contributor = store.get(contributor_id)
            if contributor is None:
                raise HTTPException(404, "contributor not found")
        with open_contribution_store() as cstore:
            their = cstore.list_by_contributor(contributor_id)
            return {
                **_serialize_contributor(contributor),
                "contributions": [
                    _serialize_contribution(
                        c,
                        cstore.get_status(c.contribution_id),
                        cstore.vote_tally(c.contribution_id),
                    )
                    for c in their
                ],
            }

    # Contributor signup is now handled via Firebase Auth + the wizard
    # finalisation. The server-minted-keypair `POST /v1/contributors`
    # endpoint that used to live here has been removed; if/when we need
    # to mint signed contributor identities, the flow will derive them
    # from the authenticated Firebase user and stash a keypair via
    # WebCrypto on the client.

    # ---- categories ----

    @app.get("/v1/categories", tags=["taxonomy"])
    def list_categories() -> list[dict]:
        with open_category_store() as store:
            return [_serialize_category(c) for c in store.all()]

    # ---- lineages ----

    @app.get("/v1/lineages/{lineage_id}", tags=["contributions"])
    def get_lineage(lineage_id: str = Path(...)) -> dict:
        with open_contribution_store() as store:
            versions = store.list_for_lineage(lineage_id)
            if not versions:
                raise HTTPException(404, "lineage not found")
            current = store.current_for_lineage(lineage_id)
            statuses = {
                v.contribution_id: store.get_status(v.contribution_id) for v in versions
            }
            return {
                "lineage_id": lineage_id,
                "current_contribution_id": (
                    current.contribution_id if current else None
                ),
                "versions": [
                    _serialize_contribution(
                        v,
                        statuses[v.contribution_id],
                        store.vote_tally(v.contribution_id),
                    )
                    for v in versions
                ],
            }

    # ---- agreement ----

    @app.get("/v1/agreement", tags=["meta"])
    def get_agreement() -> dict:
        a = current_agreement()
        return {
            "version": a.version,
            "text": a.text,
            "effective_at": a.effective_at,
            "tiers": [{"value": int(t), "name": t.name} for t in Tier],
        }

    # ---- chat sessions ----

    def _serialize_session(s: object) -> dict:
        return {
            "session_id": s.session_id,  # type: ignore[attr-defined]
            "contributor_id": s.contributor_id,  # type: ignore[attr-defined]
            "title": s.title,  # type: ignore[attr-defined]
            "created_at": s.created_at,  # type: ignore[attr-defined]
            "updated_at": s.updated_at,  # type: ignore[attr-defined]
        }

    def _serialize_message(m: object) -> dict:
        return {
            "message_id": m.message_id,  # type: ignore[attr-defined]
            "session_id": m.session_id,  # type: ignore[attr-defined]
            "role": m.role,  # type: ignore[attr-defined]
            "content": m.content,  # type: ignore[attr-defined]
            "response": m.response,  # type: ignore[attr-defined]
            "created_at": m.created_at,  # type: ignore[attr-defined]
            "sequence_number": m.sequence_number,  # type: ignore[attr-defined]
        }

    def _owned_session(session_id: str, user: AuthenticatedUser):
        """Fetch + 404/403 the session in one shot. Returns the session
        and the live ChatStore the caller can keep using."""
        cstore = open_chat_store()
        store_ctx = cstore.__enter__()
        session = store_ctx.get_session(session_id)
        if session is None:
            cstore.__exit__(None, None, None)
            raise HTTPException(404, "session not found")
        if session.contributor_id != user.uid:
            cstore.__exit__(None, None, None)
            raise HTTPException(403, "session belongs to another contributor")
        return store_ctx, cstore, session

    @app.get("/v1/chat/sessions", tags=["chat"])
    def list_chat_sessions(
        user: AuthenticatedUser = Depends(require_user),
    ) -> list[dict]:
        with open_chat_store() as cstore:
            return [_serialize_session(s) for s in cstore.list_sessions(user.uid)]

    @app.post("/v1/chat/sessions", tags=["chat"], status_code=201)
    def create_chat_session(
        payload: dict = Body(default={}),
        user: AuthenticatedUser = Depends(require_user),
    ) -> dict:
        title = (payload.get("title") or DEFAULT_TITLE).strip() or DEFAULT_TITLE
        with open_chat_store() as cstore:
            session = cstore.create_session(user.uid, title)
        return _serialize_session(session)

    @app.get("/v1/chat/sessions/{session_id}", tags=["chat"])
    def get_chat_session(
        session_id: str = Path(...),
        user: AuthenticatedUser = Depends(require_user),
    ) -> dict:
        store_ctx, cstore, session = _owned_session(session_id, user)
        try:
            messages = store_ctx.list_messages(session_id)
        finally:
            cstore.__exit__(None, None, None)
        return {
            **_serialize_session(session),
            "messages": [_serialize_message(m) for m in messages],
        }

    @app.delete("/v1/chat/sessions/{session_id}", tags=["chat"], status_code=204)
    def delete_chat_session(
        session_id: str = Path(...),
        user: AuthenticatedUser = Depends(require_user),
    ) -> None:
        store_ctx, cstore, _ = _owned_session(session_id, user)
        try:
            store_ctx.delete_session(session_id)
        finally:
            cstore.__exit__(None, None, None)

    @app.patch("/v1/chat/sessions/{session_id}", tags=["chat"])
    def rename_chat_session(
        session_id: str = Path(...),
        payload: dict = Body(...),
        user: AuthenticatedUser = Depends(require_user),
    ) -> dict:
        title = (payload.get("title") or "").strip()
        if not title:
            raise HTTPException(400, "title is required")
        if len(title) > 80:
            title = title[:80].rstrip() + "…"
        store_ctx, cstore, _ = _owned_session(session_id, user)
        try:
            store_ctx.set_session_title(session_id, title)
            session = store_ctx.get_session(session_id)
        finally:
            cstore.__exit__(None, None, None)
        assert session is not None
        return _serialize_session(session)

    @app.post(
        "/v1/chat/sessions/{session_id}/messages/{message_id}/feedback",
        tags=["chat"],
    )
    def submit_message_feedback(
        session_id: str = Path(...),
        message_id: str = Path(...),
        payload: dict = Body(...),
        user: AuthenticatedUser = Depends(require_user),
    ) -> dict:
        """Rate a network answer (+1 helpful / -1 not). This is the quality signal
        the payout layer reads: the answer's grounding set is on the message, so a
        rating attaches to the contributors who shaped it (build-direction.md)."""
        rating = payload.get("rating")
        if rating not in (-1, 1):
            raise HTTPException(400, "rating must be -1 or 1")
        comment = (payload.get("comment") or "").strip() or None
        store_ctx, cstore, _ = _owned_session(session_id, user)
        try:
            msg = store_ctx.get_message(message_id)
            if msg is None or msg.session_id != session_id:
                raise HTTPException(404, "message not found")
            if msg.role != ROLE_NETWORK:
                raise HTTPException(400, "feedback is only for network answers")
            fb = store_ctx.set_feedback(
                message_id, contributor_id=user.uid, rating=rating, comment=comment
            )
        finally:
            cstore.__exit__(None, None, None)
        return {
            "message_id": fb.message_id,
            "rating": fb.rating,
            "comment": fb.comment,
            "updated_at": fb.updated_at,
        }

    @app.post("/v1/chat/sessions/{session_id}/stream", tags=["chat"])
    async def stream_chat_message(
        session_id: str = Path(...),
        payload: dict = Body(...),
        user: AuthenticatedUser = Depends(require_user),
    ) -> StreamingResponse:
        """NDJSON stream with real model deltas.

        Routing + retrieval run sync up front; the model call goes
        through `model.stream(...)` for live deltas. Each delta becomes
        one `{"chunk": "..."}` event on the wire so the client
        typewrites at the model's actual cadence.

        User message is persisted before the stream starts; network
        message is persisted only after the full answer has streamed.
        A mid-stream abort still leaves a valid user-only conversation
        in the DB.
        """
        text = (payload.get("text") or "").strip()
        if not text:
            raise HTTPException(400, "text is required")
        with open_chat_store() as cstore:
            session = cstore.get_session(session_id)
            if session is None:
                raise HTTPException(404, "session not found")
            if session.contributor_id != user.uid:
                raise HTTPException(403, "session belongs to another contributor")
            cstore.add_message(session_id, ROLE_USER, text)

        async def gen() -> AsyncIterator[bytes]:
            def event(payload_obj: dict) -> bytes:
                return (json.dumps(payload_obj) + "\n").encode()

            # Yield "thinking" before doing any work so the UI flashes
            # the placeholder within ~10ms of the request landing.
            yield event({"stage": "thinking"})

            # Skip routing entirely for small-talk / trivial inputs.
            trivial = _is_trivial_query(text)

            category: Category | None = None
            if not trivial:
                try:
                    router_inst = _build_router()
                    routing = router_inst.route(text, top_k=1)
                except CompositionError:
                    routing = None
                if routing is not None and routing.selected:
                    category = routing.selected[0].category

            retrieved: tuple = ()
            if category is not None:
                yield event({"stage": "drawing_from_contributors"})
                await asyncio.sleep(0)
                with open_contribution_store() as store:
                    retriever = Retriever(store)
                    retrieved = tuple(
                        retriever.retrieve(
                            text, category.category_id, top_k=_config.retrieve_top_k
                        )
                    )
                system_prompt = _augment_system_prompt(
                    category.system_prompt,
                    tuple(sc.contribution for sc in retrieved),
                )
            else:
                system_prompt = DEFAULT_ASSISTANT_PROMPT

            yield event({"stage": "answering"})
            model = _model()
            collected: list[str] = []
            stream_iter = model.stream(system=system_prompt, user=text)

            def next_chunk() -> str | None:
                try:
                    return next(stream_iter)
                except StopIteration:
                    return None

            while True:
                chunk = await asyncio.to_thread(next_chunk)
                if chunk is None:
                    break
                collected.append(chunk)
                yield event({"chunk": chunk})

            full_text = "".join(collected)
            if not full_text:
                # Don't surface a hard error — emit a soft apology so the
                # chat stays usable.
                full_text = "Sorry — I didn't get a response from the model. Try again?"
                yield event({"chunk": full_text})

            # Minimal response envelope persisted alongside the message.
            # The user-facing surface doesn't show citations; this dict
            # records the grounding category + which contributions were
            # retrieved so the attribution ledger can credit them
            # server-side later.
            response_dict = {
                "query": text,
                "category_id": category.category_id if category else None,
                "retrieved_contribution_ids": [
                    sc.contribution.contribution_id for sc in retrieved
                ],
                "final_answer": full_text,
            }

            # Persist the network message and figure out whether this
            # session is due for an auto-title. We re-title:
            #   - on the very first user message (title is still DEFAULT_TITLE)
            #   - every N additional user messages thereafter
            # The model call for the title runs after `done` so the user
            # sees the answer immediately and the title resolves a beat
            # later as a `{"title": "..."}` event.
            with open_chat_store() as cstore:
                cstore.add_message(
                    session_id,
                    ROLE_NETWORK,
                    full_text,
                    response_dict,
                )
                session = cstore.get_session(session_id)
                user_message_count = sum(
                    1 for m in cstore.list_messages(session_id) if m.role == ROLE_USER
                )

            yield event({"done": response_dict})

            should_retitle = session is not None and (
                session.title == DEFAULT_TITLE
                or (user_message_count > 0 and user_message_count % 6 == 0)
            )
            if should_retitle:
                title = await asyncio.to_thread(
                    _generate_session_title, model, text, full_text
                )
                if title:
                    with open_chat_store() as cstore:
                        cstore.set_session_title(session_id, title)
                    yield event({"title": title})

        return StreamingResponse(gen(), media_type="application/x-ndjson")

    return app


def _title_for(text: str) -> str:
    """Auto-title a session from its first message — clipped to ~48 chars
    and stripped of trailing whitespace / punctuation. Fallback when the
    model-based title generator isn't run."""
    title = text.strip().splitlines()[0] if text.strip() else DEFAULT_TITLE
    if len(title) > 48:
        title = title[:47].rstrip() + "…"
    return title or DEFAULT_TITLE


_TITLE_SYSTEM_PROMPT = (
    "You name chat sessions. Given a question and its answer, return ONE "
    "title of 3 to 6 words that captures the topic. Plain text, no "
    "quotes, no trailing punctuation, no markdown. Title-case if natural."
)


# Used when the router can't match the user's question to any
# contributor-grounded category above threshold. The chat experience
# stays useful — the base model answers directly without an augmented
# system prompt.
DEFAULT_ASSISTANT_PROMPT = (
    "You are DeQuorum, a helpful, plainspoken AI assistant. Answer the "
    "user's question directly and clearly. Be conversational. If you "
    "don't know something, say so plainly. Use markdown sparingly — only "
    "when it improves readability."
)


def _generate_session_title(model: object, question: str, answer: str) -> str:
    """Ask the model for a tight title. Falls back to `_title_for` on
    any failure so the streaming endpoint never errors over a cosmetic
    title call."""
    user_prompt = (
        f"Question:\n{question}\n\nAnswer (first 600 chars):\n{answer[:600]}\n\nTitle:"
    )
    try:
        raw = model.complete(  # type: ignore[attr-defined]
            system=_TITLE_SYSTEM_PROMPT, user=user_prompt
        )
    except Exception:
        return _title_for(question)
    # Clean up: take first line, strip quotes + trailing punctuation,
    # cap at 60 chars.
    line = raw.strip().splitlines()[0] if raw.strip() else ""
    line = line.strip(" \"'`")
    line = line.rstrip(".!?;:,")
    if not line:
        return _title_for(question)
    if len(line) > 60:
        line = line[:59].rstrip() + "…"
    return line
