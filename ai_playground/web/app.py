"""FastAPI app factory: routes for trace viewer, peer review, directories."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ai_playground.base_model import BaseModel, MockBaseModel, OllamaBaseModel
from ai_playground.composition import make_strategy
from ai_playground.contribution_store import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    ContributionStore,
)
from ai_playground.contributions import Contribution
from ai_playground.core.errors import CompositionError
from ai_playground.embedder import SentenceTransformerEmbedder
from ai_playground.experts import ExpertRegistry
from ai_playground.pipeline import Pipeline
from ai_playground.retrieval import Retriever
from ai_playground.review import (
    APPROVAL_THRESHOLD,
    REJECTION_THRESHOLD,
    ReviewService,
)
from ai_playground.router import EmbeddingRouter, KeywordRouter
from ai_playground.seed_contributions import populate as populate_seed_contributions
from ai_playground.seed_experts import build_seed_registry

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class AppConfig:
    db_path: str = "./.ai_playground.db"
    use_mock: bool = False
    ollama_model: str = "qwen2.5-coder:7b"
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
        threshold = 0.25 if _config.min_score is None else _config.min_score
        return EmbeddingRouter(registry, embedder, min_score=threshold)
    threshold = 1.0 if _config.min_score is None else _config.min_score
    return KeywordRouter(registry, min_score=threshold)


def _open_store() -> ContributionStore:
    path = _config.db_path
    is_new = path == ":memory:" or not Path(path).exists()
    store = ContributionStore(path)
    if is_new and len(store) == 0:
        populate_seed_contributions(store)
    return store


def _model() -> BaseModel:
    if _config.use_mock:
        return MockBaseModel()
    return OllamaBaseModel(model=_config.ollama_model, host=_config.ollama_host)


def create_app() -> FastAPI:
    app = FastAPI(title="ai-playground")
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
        with _open_store() as store:
            service = ReviewService(store, registry=registry)
            try:
                service.cast_vote(
                    contribution_id=contribution_id,
                    voter_id=voter_id,
                    score=score,
                )
            except CompositionError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(url=next_url, status_code=303)

    @app.post("/contributions")
    def submit_contribution(
        expert_id: str = Form(...),
        text: str = Form(...),
        citations: str = Form(""),
    ) -> RedirectResponse:
        if expert_id not in registry:
            raise HTTPException(
                status_code=400, detail=f"unknown expert: {expert_id!r}"
            )
        expert = registry.get(expert_id)
        cite_list = tuple(
            line.strip() for line in citations.splitlines() if line.strip()
        )
        contribution = Contribution.create(
            expert_id=expert.expert_id,
            contributor_id=expert.expert_id,
            text=text.strip(),
            citations=cite_list,
            signing_key=expert.signing_key,
        )
        with _open_store() as store:
            store.add(contribution, status=STATUS_PENDING)
        return RedirectResponse(
            url=f"/contributions/{contribution.contribution_id}",
            status_code=303,
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
