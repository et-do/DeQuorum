"""FastAPI app factory: routes for trace viewer, peer review, directories."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from dequorum.core.errors import CompositionError
from dequorum.experts import ExpertRegistry
from dequorum.experts.seeds import build_seed_registry
from dequorum.identity.agreement import current_agreement
from dequorum.identity.contributor import Contributor, Tier
from dequorum.identity.seeds import (
    populate as populate_seed_contributors,
)
from dequorum.identity.seeds import (
    seed_contributor_for,
)
from dequorum.identity.store import IdentityStore
from dequorum.inference.base_model import BaseModel, MockBaseModel, OllamaBaseModel
from dequorum.inference.composition import make_strategy
from dequorum.inference.pipeline import Pipeline
from dequorum.intake import DuplicateDetector, SubmissionPipeline
from dequorum.knowledge.seeds import populate as populate_seed_contributions
from dequorum.knowledge.store import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    ContributionStore,
)
from dequorum.retrieval import Retriever
from dequorum.review.service import (
    APPROVAL_THRESHOLD,
    REJECTION_THRESHOLD,
    ReviewService,
)
from dequorum.routing import EmbeddingRouter, KeywordRouter
from dequorum.routing.embedder import SentenceTransformerEmbedder
from dequorum.taxonomy.seeds import (
    EXPERT_DEFAULT_CATEGORY,
)
from dequorum.taxonomy.seeds import (
    populate as populate_seed_categories,
)
from dequorum.taxonomy.store import CategoryStore

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class AppConfig:
    db_path: str = "./.dequorum.db"
    identity_db_path: str = "./.dequorum-identity.db"
    category_db_path: str = "./.dequorum-categories.db"
    use_mock: bool = False
    # Empty string = look up DEFAULT_BASE_MODEL_ID from inference/models.py
    # at request time so changing the registry default takes effect without
    # restarting the app's process state.
    ollama_model: str = ""
    ollama_host: str = "http://localhost:11434"
    top_k: int = 2
    retrieve_top_k: int = 3
    router: str = "embedding"  # "embedding" | "keyword"
    min_score: float | None = None
    composition: str = "pick_best"  # "pick_best" | "concat"
    extras: dict = field(default_factory=dict)


_config = AppConfig()


def configure_app(
    *,
    db_path: str | None = None,
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
    if db_path is not None:
        _config.db_path = db_path
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


def _open_store() -> ContributionStore:
    path = _config.db_path
    is_new = path == ":memory:" or not Path(path).exists()
    store = ContributionStore(path)
    if is_new and len(store) == 0:
        populate_seed_contributions(store)
    return store


def _open_identity_store() -> IdentityStore:
    path = _config.identity_db_path
    is_new = path == ":memory:" or not Path(path).exists()
    store = IdentityStore(path)
    if is_new and len(store) == 0:
        populate_seed_contributors(store)
    return store


def _open_category_store() -> CategoryStore:
    path = _config.category_db_path
    is_new = path == ":memory:" or not Path(path).exists()
    store = CategoryStore(path)
    if is_new and len(store) == 0:
        populate_seed_categories(store)
    return store


def _model() -> BaseModel:
    if _config.use_mock:
        return MockBaseModel()
    return OllamaBaseModel(model=_config.ollama_model, host=_config.ollama_host)


def create_app() -> FastAPI:
    app = FastAPI(title="dequorum")
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    templates.env.globals["STATUS_APPROVED"] = STATUS_APPROVED
    templates.env.globals["STATUS_PENDING"] = STATUS_PENDING
    templates.env.globals["STATUS_REJECTED"] = STATUS_REJECTED
    templates.env.globals["APPROVAL_THRESHOLD"] = APPROVAL_THRESHOLD
    templates.env.globals["REJECTION_THRESHOLD"] = REJECTION_THRESHOLD

    registry = build_seed_registry()

    @app.get("/healthz", response_class=HTMLResponse)
    def healthz() -> str:
        return "ok"

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        with _open_store() as store:
            counts = {
                "pending": len(store.list_by_status(STATUS_PENDING)),
                "approved": len(store.list_by_status(STATUS_APPROVED)),
                "rejected": len(store.list_by_status(STATUS_REJECTED)),
            }
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "experts": registry.all(),
                "counts": counts,
                "db_path": _config.db_path,
                "use_mock": _config.use_mock,
            },
        )

    @app.get("/experts", response_class=HTMLResponse)
    def experts(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "experts.html",
            {"experts": registry.all()},
        )

    @app.get("/contributions", response_class=HTMLResponse)
    def contributions_index(
        request: Request,
        expert: str | None = None,
        status: str | None = None,
    ) -> HTMLResponse:
        with _open_store() as store:
            if expert:
                contribs = store.list_for_expert(expert, status=status)
            elif status:
                contribs = store.list_by_status(status)
            else:
                contribs = list(iter(store))
            rows = [
                {
                    "contribution": c,
                    "status": store.get_status(c.contribution_id),
                    "tally": store.vote_tally(c.contribution_id),
                }
                for c in contribs
            ]
        return templates.TemplateResponse(
            request,
            "contributions.html",
            {
                "rows": rows,
                "experts": registry.all(),
                "filter_expert": expert,
                "filter_status": status,
            },
        )

    @app.get("/contributions/{contribution_id}", response_class=HTMLResponse)
    def contribution_detail(request: Request, contribution_id: str) -> HTMLResponse:
        with _open_store() as store:
            c = store.get(contribution_id)
            if c is None:
                raise HTTPException(status_code=404, detail="contribution not found")
            status = store.get_status(contribution_id)
            tally = store.vote_tally(contribution_id)
            votes = store.votes_for(contribution_id)
        return templates.TemplateResponse(
            request,
            "contribution.html",
            {
                "c": c,
                "status": status,
                "tally": tally,
                "votes": votes,
                "experts": registry.all(),
            },
        )

    @app.get("/review", response_class=HTMLResponse)
    def review_queue(request: Request) -> HTMLResponse:
        with _open_store() as store:
            contribs = store.list_by_status(STATUS_PENDING)
            rows = [
                {
                    "contribution": c,
                    "tally": store.vote_tally(c.contribution_id),
                    "votes": store.votes_for(c.contribution_id),
                }
                for c in contribs
            ]
        return templates.TemplateResponse(
            request,
            "review.html",
            {"rows": rows, "experts": registry.all()},
        )

    @app.post("/contributions/{contribution_id}/vote")
    def cast_vote(
        contribution_id: str,
        voter_id: str = Form(...),
        score: int = Form(...),
        next_url: str = Form("/review"),
    ) -> RedirectResponse:
        if voter_id not in registry:
            raise HTTPException(status_code=400, detail=f"unknown voter: {voter_id!r}")
        # Translate expert_id (form input) -> contributor_id + its signing key so
        # the self-vote check works against the new contributor identity model.
        voter_contributor, voter_key = seed_contributor_for(voter_id)
        with _open_store() as store:
            service = ReviewService(store, registry=registry)
            try:
                service.cast_vote(
                    contribution_id=contribution_id,
                    voter_id=voter_contributor.contributor_id,
                    score=score,
                    signing_key=voter_key,
                )
            except CompositionError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(url=next_url, status_code=303)

    @app.post("/contributions")
    def submit_contribution(
        expert_id: str = Form(...),
        text: str = Form(...),
        citations: str = Form(""),
        category: str = Form(""),
    ) -> RedirectResponse:
        if expert_id not in registry:
            raise HTTPException(
                status_code=400, detail=f"unknown expert: {expert_id!r}"
            )
        expert = registry.get(expert_id)
        cite_list = tuple(
            line.strip() for line in citations.splitlines() if line.strip()
        )
        category_id = category.strip() or EXPERT_DEFAULT_CATEGORY.get(
            expert.expert_id, "uncategorized"
        )
        contributor, key = seed_contributor_for(expert.expert_id)
        embedder = SentenceTransformerEmbedder()
        with _open_store() as store, _open_category_store() as cat_store:
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
                    text=text.strip(),
                    citations=cite_list,
                    primary_category_id=category_id,
                )
            except CompositionError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(
            url=f"/contributions/{result.contribution.contribution_id}",
            status_code=303,
        )

    @app.get("/onboarding", response_class=HTMLResponse)
    def onboarding_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "onboarding.html",
            {
                "agreement": current_agreement(),
                "tiers": list(Tier),
            },
        )

    @app.post("/onboarding")
    def onboarding_submit(
        display_name: str = Form(...),
        email: str = Form(""),
    ) -> RedirectResponse:
        import hashlib
        import secrets

        priv = secrets.token_bytes(32)
        pub = hashlib.blake2b(priv, digest_size=32).digest()
        email_hash = None
        if email.strip():
            email_hash = hashlib.blake2b(
                email.strip().lower().encode(), digest_size=16
            ).hexdigest()

        agreement = current_agreement()
        contributor = Contributor.create(
            display_name=display_name.strip(),
            public_key=pub,
            signing_key=priv,
            agreement_version=agreement.version,
            agreement_text=agreement.text,
            tier=Tier.EMAIL_VERIFIED if email_hash else Tier.ANONYMOUS,
            email_hash=email_hash,
        )
        with _open_identity_store() as store:
            store.add(contributor)
        return RedirectResponse(
            url=f"/contributors/{contributor.contributor_id}",
            status_code=303,
        )

    @app.get("/contributors/{contributor_id}", response_class=HTMLResponse)
    def contributor_detail(request: Request, contributor_id: str) -> HTMLResponse:
        with _open_identity_store() as store:
            contributor = store.get(contributor_id)
            if contributor is None:
                raise HTTPException(status_code=404, detail="contributor not found")
        with _open_store() as cstore:
            their_contributions = cstore.list_by_contributor(contributor_id)
        return templates.TemplateResponse(
            request,
            "contributor.html",
            {
                "contributor": contributor,
                "contributions": their_contributions,
            },
        )

    @app.get("/categories", response_class=HTMLResponse)
    def categories_page(request: Request) -> HTMLResponse:
        with _open_category_store() as store:
            categories = store.all()
        return templates.TemplateResponse(
            request,
            "categories.html",
            {"categories": categories},
        )

    @app.get("/lineages/{lineage_id}", response_class=HTMLResponse)
    def lineage_detail(request: Request, lineage_id: str) -> HTMLResponse:
        with _open_store() as store:
            versions = store.list_for_lineage(lineage_id)
            if not versions:
                raise HTTPException(status_code=404, detail="lineage not found")
            current = store.current_for_lineage(lineage_id)
            statuses = {
                v.contribution_id: store.get_status(v.contribution_id) for v in versions
            }
        return templates.TemplateResponse(
            request,
            "lineage.html",
            {
                "lineage_id": lineage_id,
                "versions": versions,
                "current": current,
                "statuses": statuses,
            },
        )

    @app.get("/query", response_class=HTMLResponse)
    def query_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "query.html",
            {
                "response": None,
                "query_text": "",
                "config": _config,
            },
        )

    @app.post("/query", response_class=HTMLResponse)
    def query_submit(request: Request, text: str = Form(...)) -> HTMLResponse:
        store = _open_store()
        try:
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
                error = None
            except CompositionError as exc:
                response = None
                error = str(exc)
        finally:
            store.close()
        return templates.TemplateResponse(
            request,
            "query.html",
            {
                "response": response,
                "query_text": text,
                "error": error,
                "config": _config,
                "ledger": pipeline.ledger.totals() if response else {},
            },
        )

    return app
