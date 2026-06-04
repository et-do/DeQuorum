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
import hashlib
import json
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field

from fastapi import Body, FastAPI, HTTPException, Path, Query
from fastapi.responses import StreamingResponse

from dequorum.core.errors import CompositionError
from dequorum.db import (
    DEFAULT_DATABASE_URL,
    close_pool,
    init_pool,
    open_category_store,
    open_contribution_store,
    open_identity_store,
)
from dequorum.db.migrate import upgrade_to_head
from dequorum.experts import ExpertRegistry
from dequorum.experts.seeds import build_seed_registry
from dequorum.identity.agreement import current_agreement
from dequorum.identity.contributor import Contributor, Tier
from dequorum.identity.seeds import populate as populate_seed_contributors
from dequorum.identity.seeds import seed_contributor_for
from dequorum.inference.base_model import BaseModel, MockBaseModel, OllamaBaseModel
from dequorum.inference.composition import make_strategy
from dequorum.inference.pipeline import Pipeline
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
from dequorum.taxonomy.seeds import EXPERT_DEFAULT_CATEGORY
from dequorum.taxonomy.seeds import populate as populate_seed_categories


@dataclass
class AppConfig:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DEQUORUM_DATABASE_URL", DEFAULT_DATABASE_URL
        )
    )
    use_mock: bool = False
    ollama_model: str = ""
    # Honor DEQUORUM_OLLAMA_HOST so compose's "http://ollama:11434" reaches
    # the app. Falls back to localhost for standalone `dequorum serve`.
    ollama_host: str = field(
        default_factory=lambda: os.environ.get(
            "DEQUORUM_OLLAMA_HOST", "http://localhost:11434"
        )
    )
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


def _build_router(registry: ExpertRegistry) -> EmbeddingRouter | KeywordRouter:
    if _config.router == "embedding":
        embedder = SentenceTransformerEmbedder()
        threshold = 0.18 if _config.min_score is None else _config.min_score
        fallback = KeywordRouter(registry, fallback_to_all=False, min_score=1.0)
        return EmbeddingRouter(
            registry, embedder, min_score=threshold, fallback=fallback
        )
    threshold = 1.0 if _config.min_score is None else _config.min_score
    return KeywordRouter(registry, min_score=threshold)


def _model() -> BaseModel:
    if _config.use_mock:
        return MockBaseModel()
    return OllamaBaseModel(model=_config.ollama_model, host=_config.ollama_host)


def _seed_if_empty() -> None:
    """Idempotent: insert seed rows only if their tables are empty."""
    with open_identity_store() as istore:
        istore.ensure_seed_agreements()
        if len(istore) == 0:
            populate_seed_contributors(istore)
    with open_contribution_store() as cstore:
        if len(cstore) == 0:
            populate_seed_contributions(cstore)
    with open_category_store() as cat_store:
        if len(cat_store) == 0:
            populate_seed_categories(cat_store)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_pool(_config.database_url)
    upgrade_to_head(_config.database_url)
    _seed_if_empty()
    try:
        yield
    finally:
        close_pool()


# --- serialization helpers ------------------------------------------------


def _serialize_expert(expert: object) -> dict:
    return {
        "expert_id": expert.expert_id,  # type: ignore[attr-defined]
        "display_name": expert.display_name,  # type: ignore[attr-defined]
        "specialty_tags": list(expert.specialty_tags),  # type: ignore[attr-defined]
        "prompt_digest": expert.prompt_digest,  # type: ignore[attr-defined]
        "example_questions": list(getattr(expert, "example_questions", ()) or ()),
    }


def _serialize_contribution(c: object, status: str | None, tally: int) -> dict:
    return {
        "contribution_id": c.contribution_id,  # type: ignore[attr-defined]
        "lineage_id": c.lineage_id,  # type: ignore[attr-defined]
        "version_number": c.version_number,  # type: ignore[attr-defined]
        "parent_version": c.parent_version,  # type: ignore[attr-defined]
        "expert_id": c.expert_id,  # type: ignore[attr-defined]
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
        "tier": int(c.tier),  # type: ignore[attr-defined]
        "tier_name": c.tier.name,  # type: ignore[attr-defined]
        "agreement_version": c.agreement_version,  # type: ignore[attr-defined]
        "vote_weight": c.vote_weight,  # type: ignore[attr-defined]
        "daily_submission_cap": c.daily_submission_cap,  # type: ignore[attr-defined]
        "has_email": c.email_hash is not None,  # type: ignore[attr-defined]
        "created_at": c.created_at,  # type: ignore[attr-defined]
    }


def _serialize_category(cat: object) -> dict:
    return {
        "category_id": cat.category_id,  # type: ignore[attr-defined]
        "parent_id": cat.parent_id,  # type: ignore[attr-defined]
        "display_name": cat.display_name,  # type: ignore[attr-defined]
        "depth": cat.depth,  # type: ignore[attr-defined]
        "description": cat.description,  # type: ignore[attr-defined]
    }


def create_app() -> FastAPI:
    app = FastAPI(
        title="dequorum",
        description="DeQuorum JSON API. UI is served by services/frontend (React).",
        version="0.1.0",
        lifespan=_lifespan,
    )
    registry = build_seed_registry()

    # ---- health + meta ----

    @app.get("/v1/healthz", tags=["meta"])
    def healthz() -> dict:
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

    # ---- experts ----

    @app.get("/v1/experts", tags=["experts"])
    def list_experts() -> list[dict]:
        return [_serialize_expert(e) for e in registry.all()]

    # ---- contributions ----

    @app.get("/v1/contributions", tags=["contributions"])
    def list_contributions(
        expert: str | None = Query(None),
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
            if expert:
                contribs = store.list_for_expert(expert, status=status)
            elif contributor:
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

    @app.post("/v1/contributions", tags=["contributions"], status_code=201)
    def submit_contribution(payload: dict = Body(...)) -> dict:
        expert_id = payload.get("expert_id")
        text = (payload.get("text") or "").strip()
        citations = tuple(c.strip() for c in payload.get("citations", []) if c.strip())
        category = (payload.get("primary_category_id") or "").strip()
        if not expert_id or expert_id not in registry:
            raise HTTPException(400, f"unknown expert: {expert_id!r}")
        if not text:
            raise HTTPException(400, "text is required")
        expert = registry.get(expert_id)
        category_id = category or EXPERT_DEFAULT_CATEGORY.get(
            expert.expert_id, "uncategorized"
        )
        contributor, key = seed_contributor_for(expert.expert_id)
        embedder = SentenceTransformerEmbedder()
        with open_contribution_store() as store, open_category_store() as cat_store:
            pipeline = SubmissionPipeline(
                contribution_store=store,
                category_store=cat_store,
                duplicate_detector=DuplicateDetector(store, embedder),
            )
            try:
                result = pipeline.submit(
                    contributor=contributor,
                    contributor_signing_key=key,
                    expert_id=expert.expert_id,
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
    ) -> dict:
        voter_id = payload.get("voter_id")
        score = payload.get("score")
        if voter_id is None or voter_id not in registry:
            raise HTTPException(400, f"unknown voter: {voter_id!r}")
        if score not in (-1, 0, 1):
            raise HTTPException(400, "score must be -1, 0, or 1")
        voter_contributor, voter_key = seed_contributor_for(voter_id)
        with open_contribution_store() as store:
            service = ReviewService(store, registry=registry)
            try:
                outcome = service.cast_vote(
                    contribution_id=contribution_id,
                    voter_id=voter_contributor.contributor_id,
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

    @app.post("/v1/contributors", tags=["contributors"], status_code=201)
    def create_contributor(payload: dict = Body(...)) -> dict:
        display_name = (payload.get("display_name") or "").strip()
        email = (payload.get("email") or "").strip()
        if not display_name:
            raise HTTPException(400, "display_name is required")

        priv = secrets.token_bytes(32)
        pub = hashlib.blake2b(priv, digest_size=32).digest()
        email_hash = None
        if email:
            email_hash = hashlib.blake2b(
                email.lower().encode(), digest_size=16
            ).hexdigest()

        agreement = current_agreement()
        contributor = Contributor.create(
            display_name=display_name,
            public_key=pub,
            signing_key=priv,
            agreement_version=agreement.version,
            agreement_text=agreement.text,
            tier=Tier.EMAIL_VERIFIED if email_hash else Tier.ANONYMOUS,
            email_hash=email_hash,
        )
        with open_identity_store() as store:
            store.add(contributor)
        return {
            **_serialize_contributor(contributor),
            "private_key_hex": priv.hex(),  # dev only
            "warning": (
                "Save private_key_hex SECURELY. Real signups use client-side "
                "WebCrypto and never transmit the private key over the wire."
            ),
        }

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

    # ---- queries ----

    @app.post("/v1/queries", tags=["queries"])
    def run_query(payload: dict = Body(...)) -> dict:
        text = (payload.get("text") or "").strip()
        if not text:
            raise HTTPException(400, "text is required")
        with open_contribution_store() as store:
            pipeline = Pipeline(
                router=_build_router(registry),
                model=_model(),
                retriever=Retriever(store),
                composition=make_strategy(_config.composition),
                top_k=_config.top_k,
                retrieve_top_k=_config.retrieve_top_k,
            )
            try:
                response = pipeline.query(text)
            except CompositionError as exc:
                raise HTTPException(400, str(exc)) from exc
            ledger = pipeline.ledger.totals()
        return {
            "query": response.query,
            "routing": {
                "method": response.routing.method,
                "matched_tags": list(response.routing.matched_tags),
                "fallback_used": response.routing.fallback_used,
                "threshold": response.routing.threshold,
                "selected": [
                    {"expert_id": s.expert.expert_id, "score": round(s.score, 4)}
                    for s in response.routing.selected
                ],
            },
            "experts": [
                {
                    "expert_id": a.expert.expert_id,
                    "routing_score": round(a.routing_score, 4),
                    "answer": a.answer,
                    "signature": asdict(a.signature),
                    "retrieved": [
                        {
                            "contribution_id": sc.contribution.contribution_id,
                            "contributor_id": sc.contribution.contributor_id,
                            "score": round(sc.score, 4),
                            "text": sc.contribution.text,
                            "citations": list(sc.contribution.citations),
                        }
                        for sc in a.retrieved
                    ],
                }
                for a in response.expert_answers
            ],
            "composition": {
                "strategy": response.composition.strategy,
                "chosen": list(response.composition.chosen),
            },
            "final_answer": response.final_answer,
            "ledger": ledger,
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

    return app
