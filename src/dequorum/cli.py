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
from dequorum.identity.agreement import current_agreement
from dequorum.identity.contributor import Contributor, Tier
from dequorum.identity.seeds import (
    populate as populate_seed_contributors,
)
from dequorum.identity.seeds import (
    seed_contributor_for,
)
from dequorum.identity.store import IdentityStore
from dequorum.inference.base_model import MockBaseModel, OllamaBaseModel
from dequorum.inference.composition import make_strategy
from dequorum.inference.pipeline import Pipeline
from dequorum.intake import DuplicateDetector, SubmissionPipeline
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
from dequorum.taxonomy.seeds import (
    EXPERT_DEFAULT_CATEGORY,
)
from dequorum.taxonomy.seeds import (
    populate as populate_seed_categories,
)
from dequorum.taxonomy.store import CategoryStore

DEFAULT_DB = "./.dequorum.db"
DEFAULT_IDENTITY_DB = "./.dequorum-identity.db"
DEFAULT_CATEGORY_DB = "./.dequorum-categories.db"


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
    submit.add_argument(
        "--as",
        dest="expert_id",
        required=True,
        help="Expert persona to publish under",
    )
    submit.add_argument("--text", required=True, help="The factual claim")
    submit.add_argument(
        "--cite",
        action="append",
        default=[],
        help="Citation URL (repeatable, HTTPS only)",
    )
    submit.add_argument(
        "--category",
        default=None,
        help="Primary category id. Defaults to the expert's default category.",
    )
    submit.add_argument(
        "--block-on-duplicate",
        action="store_true",
        help="Hard-fail submission if a likely duplicate exists "
        "(default: surface and let you decide)",
    )
    submit.add_argument("--db", default=DEFAULT_DB)
    submit.add_argument("--category-db", default=DEFAULT_CATEGORY_DB)

    update = sub.add_parser(
        "update", help="Submit a new version of an existing approved contribution"
    )
    update.add_argument(
        "--as",
        dest="expert_id",
        required=True,
        help="Expert persona of the contributor making the update",
    )
    update.add_argument(
        "--lineage",
        required=True,
        help="Lineage id to update (looks up the current version automatically)",
    )
    update.add_argument("--text", required=True, help="The updated claim text")
    update.add_argument(
        "--cite", action="append", default=[], help="Citation URL (repeatable)"
    )
    update.add_argument(
        "--category",
        default=None,
        help="Optional new primary category (defaults to the existing one)",
    )
    update.add_argument("--db", default=DEFAULT_DB)
    update.add_argument("--category-db", default=DEFAULT_CATEGORY_DB)

    signup = sub.add_parser(
        "signup", help="Create a new contributor account (signs the user agreement)"
    )
    signup.add_argument("--name", required=True, help="Display name")
    signup.add_argument(
        "--email", default=None, help="Optional email (recorded as hash)"
    )
    signup.add_argument(
        "--seed-key",
        default=None,
        help="(dev only) Deterministic seed phrase for the keypair; default is random.",
    )
    signup.add_argument("--identity-db", default=DEFAULT_IDENTITY_DB)

    list_cat = sub.add_parser("categories", help="List the curated category taxonomy")
    list_cat.add_argument(
        "--category-db",
        default=DEFAULT_CATEGORY_DB,
        help="Category DB path",
    )

    list_contrib = sub.add_parser(
        "list-contributors", help="List signed-up contributors"
    )
    list_contrib.add_argument("--identity-db", default=DEFAULT_IDENTITY_DB)

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

    bench = sub.add_parser(
        "benchmark",
        help="Quality check: vanilla vs DeQuorum-full vs DeQuorum-no-retrieval",
    )
    bench.add_argument(
        "--mock", action="store_true", help="Use mock model (smoke test)"
    )
    bench.add_argument("--model", default="qwen2.5-coder:7b", help="Ollama model tag")
    bench.add_argument("--host", default="http://localhost:11434", help="Ollama host")
    bench.add_argument(
        "--router", choices=("keyword", "embedding"), default="embedding"
    )
    bench.add_argument("--min-score", type=float, default=None)
    bench.add_argument("--top-k", type=int, default=2)
    bench.add_argument("--retrieve-top-k", type=int, default=3)
    bench.add_argument("--db", default=DEFAULT_DB)
    bench.add_argument(
        "--output",
        default="docs/benchmarks/report.md",
        help="Where to write the Markdown report (parent dir is auto-created)",
    )
    bench.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N questions (smoke testing)",
    )

    return parser


def _open_store(path: str) -> ContributionStore:
    """Open the store at path and seed it on first use if empty."""
    is_new = path == ":memory:" or not Path(path).exists()
    store = ContributionStore(path)
    if is_new and len(store) == 0:
        populate_seed_contributions(store)
    return store


def _open_identity_store(path: str) -> IdentityStore:
    """Open the identity store at path and seed it on first use if empty."""
    is_new = path == ":memory:" or not Path(path).exists()
    store = IdentityStore(path)
    if is_new and len(store) == 0:
        populate_seed_contributors(store)
    return store


def _open_category_store(path: str) -> CategoryStore:
    """Open the category store at path and seed it on first use if empty."""
    is_new = path == ":memory:" or not Path(path).exists()
    store = CategoryStore(path)
    if is_new and len(store) == 0:
        populate_seed_categories(store)
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
        threshold = 0.18 if min_score is None else min_score
        # Keyword router as a deterministic safety net: catches obvious matches
        # where embedding similarity dipped below the threshold for a relevant expert.
        fallback = KeywordRouter(registry, fallback_to_all=False, min_score=1.0)
        return EmbeddingRouter(
            registry, embedder, min_score=threshold, fallback=fallback
        )
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

    contributor, contributor_key = seed_contributor_for(expert.expert_id)
    category = args.category or EXPERT_DEFAULT_CATEGORY.get(
        expert.expert_id, "uncategorized"
    )

    embedder = SentenceTransformerEmbedder()
    with (
        _open_store(args.db) as store,
        _open_category_store(args.category_db) as cat_store,
    ):
        pipeline = SubmissionPipeline(
            contribution_store=store,
            category_store=cat_store,
            duplicate_detector=DuplicateDetector(store, embedder),
            block_on_likely_duplicate=args.block_on_duplicate,
        )
        try:
            result = pipeline.submit(
                contributor=contributor,
                contributor_signing_key=contributor_key,
                expert_id=expert.expert_id,
                text=args.text,
                citations=tuple(args.cite),
                primary_category_id=category,
            )
        except CompositionError as exc:
            print(json.dumps({"error": str(exc)}, indent=2))
            return 1
        total = len(store)

    contribution = result.contribution
    print(
        json.dumps(
            {
                "contribution_id": contribution.contribution_id,
                "lineage_id": contribution.lineage_id,
                "version_number": contribution.version_number,
                "expert_id": contribution.expert_id,
                "contributor_id": contribution.contributor_id,
                "primary_category_id": contribution.primary_category_id,
                "status": STATUS_PENDING,
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
                "signature": asdict(contribution.signature),
                "store_total": total,
                "db": args.db,
            },
            indent=2,
        )
    )
    return 0


def _cmd_update(args: argparse.Namespace) -> int:
    registry = build_seed_registry()
    try:
        expert = registry.get(args.expert_id)
    except KeyError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1

    contributor, contributor_key = seed_contributor_for(expert.expert_id)

    with (
        _open_store(args.db) as store,
        _open_category_store(args.category_db) as cat_store,
    ):
        current_contribution = store.current_for_lineage(args.lineage)
        if current_contribution is None:
            # Fall back: latest version of the lineage (covers pending lineages too)
            existing = store.list_for_lineage(args.lineage)
            if not existing:
                print(
                    json.dumps({"error": f"unknown lineage {args.lineage!r}"}, indent=2)
                )
                return 1
            current_contribution = existing[-1]

        category = args.category or current_contribution.primary_category_id
        pipeline = SubmissionPipeline(
            contribution_store=store,
            category_store=cat_store,
            duplicate_detector=None,  # updates skip dedup by design
        )
        try:
            result = pipeline.submit(
                contributor=contributor,
                contributor_signing_key=contributor_key,
                expert_id=expert.expert_id,
                text=args.text,
                citations=tuple(args.cite),
                primary_category_id=category,
                update_lineage_id=args.lineage,
            )
        except CompositionError as exc:
            print(json.dumps({"error": str(exc)}, indent=2))
            return 1

    contribution = result.contribution
    print(
        json.dumps(
            {
                "contribution_id": contribution.contribution_id,
                "lineage_id": contribution.lineage_id,
                "version_number": contribution.version_number,
                "parent_version": contribution.parent_version,
                "expert_id": contribution.expert_id,
                "contributor_id": contribution.contributor_id,
                "status": STATUS_PENDING,
                "db": args.db,
            },
            indent=2,
        )
    )
    return 0


def _cmd_signup(args: argparse.Namespace) -> int:
    import hashlib
    import secrets

    if args.seed_key:
        priv = args.seed_key.encode().ljust(32, b"\x00")[:32]
        pub = b"pubkey-from-seed-" + priv[:8]
    else:
        priv = secrets.token_bytes(32)
        pub = hashlib.blake2b(priv, digest_size=32).digest()

    email_hash = None
    if args.email:
        email_hash = hashlib.blake2b(
            args.email.strip().lower().encode(), digest_size=16
        ).hexdigest()

    agreement = current_agreement()
    contributor = Contributor.create(
        display_name=args.name,
        public_key=pub,
        signing_key=priv,
        agreement_version=agreement.version,
        agreement_text=agreement.text,
        tier=Tier.EMAIL_VERIFIED if args.email else Tier.ANONYMOUS,
        email_hash=email_hash,
    )

    with _open_identity_store(args.identity_db) as store:
        store.add(contributor)
        total = len(store)

    print(
        json.dumps(
            {
                "contributor_id": contributor.contributor_id,
                "display_name": contributor.display_name,
                "tier": int(contributor.tier),
                "tier_name": contributor.tier.name,
                "agreement_version": contributor.agreement_version,
                "vote_weight": contributor.vote_weight,
                "daily_submission_cap": contributor.daily_submission_cap,
                "private_key_hex": priv.hex(),  # dev only; real signups never expose this
                "public_key_hex": contributor.public_key.hex(),
                "store_total": total,
                "warning": (
                    "Save private_key_hex SECURELY. The network cannot recover it. "
                    "Real signups use client-side WebCrypto and never transmit the "
                    "private key over the wire."
                ),
            },
            indent=2,
        )
    )
    return 0


def _cmd_list_categories(args: argparse.Namespace) -> int:
    with _open_category_store(args.category_db) as store:
        payload = [
            {
                "category_id": c.category_id,
                "parent_id": c.parent_id,
                "display_name": c.display_name,
                "depth": c.depth,
                "description": c.description,
            }
            for c in store.all()
        ]
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_list_contributors(args: argparse.Namespace) -> int:
    with _open_identity_store(args.identity_db) as store:
        payload = [
            {
                "contributor_id": c.contributor_id,
                "display_name": c.display_name,
                "tier": int(c.tier),
                "tier_name": c.tier.name,
                "vote_weight": c.vote_weight,
                "agreement_version": c.agreement_version,
                "has_email": c.email_hash is not None,
            }
            for c in store.list_all()
        ]
    print(json.dumps(payload, indent=2))
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


def _cmd_benchmark(args: argparse.Namespace) -> int:
    from dequorum.benchmark import SEED_QUESTIONS, run_benchmark
    from dequorum.benchmark.runner import write_markdown_report

    registry = build_seed_registry()
    store = _open_store(args.db)

    def router_factory(reg: ExpertRegistry) -> object:
        return _build_router(reg, args.router, args.min_score)

    model: MockBaseModel | OllamaBaseModel = (
        MockBaseModel()
        if args.mock
        else OllamaBaseModel(model=args.model, host=args.host)
    )
    model_label = "mock" if args.mock else args.model

    questions = SEED_QUESTIONS if args.limit is None else SEED_QUESTIONS[: args.limit]

    def progress(i: int, total: int, text: str) -> None:
        print(f"  [{i}/{total}] {text[:80]}", flush=True)

    total = len(questions) * 3
    print(f"Running {len(questions)} questions x 3 conditions = {total} generations...")
    try:
        report = run_benchmark(
            questions=questions,
            model=model,
            registry=registry,
            store=store,
            router_factory=router_factory,
            top_k=args.top_k,
            retrieve_top_k=args.retrieve_top_k,
            model_label=model_label,
            progress=progress,
        )
    finally:
        store.close()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_markdown_report(report, output_path)
    print(f"\nReport written: {output_path}")
    print("Open it side-by-side with the spec and rate the answers honestly.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "query":
        return _cmd_query(args)
    if args.cmd == "submit":
        return _cmd_submit(args)
    if args.cmd == "update":
        return _cmd_update(args)
    if args.cmd == "signup":
        return _cmd_signup(args)
    if args.cmd == "categories":
        return _cmd_list_categories(args)
    if args.cmd == "list-contributors":
        return _cmd_list_contributors(args)
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
    if args.cmd == "benchmark":
        return _cmd_benchmark(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
