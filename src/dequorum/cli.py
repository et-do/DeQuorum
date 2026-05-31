"""Command-line entry point exposed by [project.scripts] in pyproject."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from dequorum.core.errors import CompositionError
from dequorum.experts import ExpertRegistry
from dequorum.experts.seeds import build_seed_registry
from dequorum.inference.base_model import MockBaseModel, OllamaBaseModel
from dequorum.inference.composition import make_strategy
from dequorum.inference.pipeline import Pipeline
from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.seeds import populate as populate_seed_contributions
from dequorum.knowledge.store import (
    STATUS_PENDING,
    VALID_STATUSES,
    ContributionStore,
)
from dequorum.retrieval import Retriever
from dequorum.review.service import ReviewService
from dequorum.routing import EmbeddingRouter, KeywordRouter
from dequorum.routing.embedder import SentenceTransformerEmbedder

DEFAULT_DB = "./.dequorum.db"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dequorum")
    sub = parser.add_subparsers(dest="cmd", required=True)

    query = sub.add_parser("query", help="Ask the expert network a question")
    query.add_argument("text", help="The query text")
    query.add_argument("--mock", action="store_true", help="Use mock model")
    query.add_argument("--model", default="qwen2.5-coder:7b", help="Ollama model tag")
    query.add_argument("--host", default="http://localhost:11434", help="Ollama host")
    query.add_argument("--top-k", type=int, default=2, help="Max experts to consult")
    query.add_argument(
        "--retrieve-top-k", type=int, default=3, help="Contributions per expert"
    )
    query.add_argument(
        "--no-retrieve",
        action="store_true",
        help="Disable contribution retrieval (compare with Week 1 behavior)",
    )
    query.add_argument(
        "--router",
        choices=("keyword", "embedding"),
        default="embedding",
        help="Routing strategy. 'embedding' is semantic; 'keyword' is the baseline.",
    )
    query.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Override the router's min-score threshold for selecting an expert",
    )
    query.add_argument(
        "--compose",
        choices=("pick_best", "concat"),
        default="pick_best",
        help="How to combine N expert answers into the final response",
    )
    query.add_argument("--db", default=DEFAULT_DB, help="Contribution DB path")

    submit = sub.add_parser(
        "submit", help="Submit a signed contribution (pending review)"
    )
    submit.add_argument("--as", dest="expert_id", required=True, help="Expert id")
    submit.add_argument("--text", required=True, help="The factual claim")
    submit.add_argument(
        "--cite", action="append", default=[], help="Citation URL (repeatable)"
    )
    submit.add_argument("--db", default=DEFAULT_DB)

    vote = sub.add_parser("vote", help="Cast a signed vote on a contribution")
    vote.add_argument("--as", dest="voter_id", required=True, help="Voter expert id")
    vote.add_argument(
        "--contribution", required=True, help="Contribution id (or prefix)"
    )
    vote.add_argument(
        "--score", type=int, required=True, choices=[-1, 0, 1], help="-1, 0, or 1"
    )
    vote.add_argument("--db", default=DEFAULT_DB)

    list_c = sub.add_parser(
        "list-contributions", help="List stored contributions with status + tally"
    )
    list_c.add_argument("--expert", default=None, help="Filter by expert id")
    list_c.add_argument(
        "--status",
        choices=sorted(VALID_STATUSES),
        default=None,
        help="Filter by status",
    )
    list_c.add_argument("--db", default=DEFAULT_DB)

    review = sub.add_parser("review", help="Show pending contributions awaiting votes")
    review.add_argument("--db", default=DEFAULT_DB)

    sub.add_parser("list-experts", help="Print the seed expert registry")

    serve = sub.add_parser("serve", help="Run the FastAPI web UI")
    serve.add_argument("--host", default="0.0.0.0", help="Bind host")
    serve.add_argument("--port", type=int, default=8000, help="Bind port")
    serve.add_argument("--db", default=DEFAULT_DB)
    serve.add_argument("--mock", action="store_true", help="Use mock model")
    serve.add_argument(
        "--router", choices=("keyword", "embedding"), default="embedding"
    )
    serve.add_argument("--min-score", type=float, default=None)
    serve.add_argument(
        "--compose", choices=("pick_best", "concat"), default="pick_best"
    )
    serve.add_argument("--reload", action="store_true", help="Auto-reload on edits")

    return parser


def _open_store(path: str) -> ContributionStore:
    """Open the store at path and seed it on first use if empty."""
    is_new = path == ":memory:" or not Path(path).exists()
    store = ContributionStore(path)
    if is_new and len(store) == 0:
        populate_seed_contributions(store)
    return store


def _resolve_contribution_id(store: ContributionStore, prefix: str) -> str | None:
    """Allow short prefixes for CLI ergonomics."""
    if store.get(prefix) is not None:
        return prefix
    matches = [c.contribution_id for c in store if c.contribution_id.startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise CompositionError(f"ambiguous contribution prefix {prefix!r}: {matches}")
    return None


def _build_router(
    registry: ExpertRegistry, kind: str, min_score: float | None
) -> EmbeddingRouter | KeywordRouter:
    if kind == "embedding":
        embedder = SentenceTransformerEmbedder()
        threshold = 0.25 if min_score is None else min_score
        return EmbeddingRouter(registry, embedder, min_score=threshold)
    threshold = 1.0 if min_score is None else min_score
    return KeywordRouter(registry, min_score=threshold)


def _cmd_query(args: argparse.Namespace) -> int:
    registry = build_seed_registry()
    router = _build_router(registry, args.router, args.min_score)
    model: MockBaseModel | OllamaBaseModel = (
        MockBaseModel()
        if args.mock
        else OllamaBaseModel(model=args.model, host=args.host)
    )

    retriever: Retriever | None = None
    store: ContributionStore | None = None
    if not args.no_retrieve:
        store = _open_store(args.db)
        retriever = Retriever(store)

    pipeline = Pipeline(
        router=router,
        model=model,
        retriever=retriever,
        composition=make_strategy(args.compose),
        top_k=args.top_k,
        retrieve_top_k=args.retrieve_top_k,
    )

    try:
        response = pipeline.query(args.text)
    except CompositionError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1
    finally:
        if store is not None:
            store.close()

    payload = {
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
        "ledger": pipeline.ledger.totals(),
    }
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_submit(args: argparse.Namespace) -> int:
    registry = build_seed_registry()
    try:
        expert = registry.get(args.expert_id)
    except KeyError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1

    contribution = Contribution.create(
        expert_id=expert.expert_id,
        contributor_id=expert.expert_id,
        text=args.text,
        citations=tuple(args.cite),
        signing_key=expert.signing_key,
    )
    with _open_store(args.db) as store:
        store.add(contribution, status=STATUS_PENDING)
        total = len(store)

    print(
        json.dumps(
            {
                "contribution_id": contribution.contribution_id,
                "expert_id": contribution.expert_id,
                "status": STATUS_PENDING,
                "signature": asdict(contribution.signature),
                "store_total": total,
                "db": args.db,
            },
            indent=2,
        )
    )
    return 0


def _cmd_vote(args: argparse.Namespace) -> int:
    registry = build_seed_registry()
    if args.voter_id not in registry:
        print(
            json.dumps({"error": f"unknown voter expert: {args.voter_id!r}"}, indent=2)
        )
        return 1

    with _open_store(args.db) as store:
        try:
            cid = _resolve_contribution_id(store, args.contribution)
        except CompositionError as exc:
            print(json.dumps({"error": str(exc)}, indent=2))
            return 1
        if cid is None:
            print(
                json.dumps(
                    {"error": f"no contribution matches {args.contribution!r}"},
                    indent=2,
                )
            )
            return 1

        service = ReviewService(store, registry=registry)
        try:
            outcome = service.cast_vote(
                contribution_id=cid, voter_id=args.voter_id, score=args.score
            )
        except CompositionError as exc:
            print(json.dumps({"error": str(exc)}, indent=2))
            return 1

    print(json.dumps(asdict(outcome), indent=2))
    return 0


def _cmd_list_contributions(args: argparse.Namespace) -> int:
    with _open_store(args.db) as store:
        if args.expert:
            contribs = store.list_for_expert(args.expert, status=args.status)
        elif args.status:
            contribs = store.list_by_status(args.status)
        else:
            contribs = list(iter(store))
        payload = [
            {
                "contribution_id": c.contribution_id,
                "expert_id": c.expert_id,
                "contributor_id": c.contributor_id,
                "status": store.get_status(c.contribution_id),
                "tally": store.vote_tally(c.contribution_id),
                "text": c.text,
                "citations": list(c.citations),
            }
            for c in contribs
        ]
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    with _open_store(args.db) as store:
        contribs = store.list_by_status(STATUS_PENDING)
        payload = [
            {
                "contribution_id": c.contribution_id,
                "expert_id": c.expert_id,
                "contributor_id": c.contributor_id,
                "tally": store.vote_tally(c.contribution_id),
                "text": c.text,
                "citations": list(c.citations),
                "votes": [
                    {"voter_id": v.voter_id, "score": v.score}
                    for v in store.votes_for(c.contribution_id)
                ],
            }
            for c in contribs
        ]
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_list_experts(_: argparse.Namespace) -> int:
    registry = build_seed_registry()
    payload = [
        {
            "expert_id": e.expert_id,
            "display_name": e.display_name,
            "specialty_tags": list(e.specialty_tags),
            "prompt_digest": e.prompt_digest,
        }
        for e in registry.all()
    ]
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from dequorum.web.app import configure_app, create_app

    configure_app(
        db_path=args.db,
        use_mock=args.mock,
        router=args.router,
        min_score=args.min_score,
        composition=args.compose,
    )
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "query":
        return _cmd_query(args)
    if args.cmd == "submit":
        return _cmd_submit(args)
    if args.cmd == "vote":
        return _cmd_vote(args)
    if args.cmd == "list-contributions":
        return _cmd_list_contributions(args)
    if args.cmd == "review":
        return _cmd_review(args)
    if args.cmd == "list-experts":
        return _cmd_list_experts(args)
    if args.cmd == "serve":
        return _cmd_serve(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
