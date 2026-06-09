"""Command-line entry point exposed by [project.scripts] in pyproject."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from dequorum.core.errors import CompositionError
from dequorum.db import (
    DEFAULT_DATABASE_URL,
    init_pool,
    open_category_store,
    open_contribution_store,
    open_identity_store,
)
from dequorum.db.migrate import upgrade_to_head
from dequorum.identity.agreement import current_agreement
from dequorum.identity.contributor import Contributor, Tier
from dequorum.identity.seeds import populate as populate_seed_contributors
from dequorum.identity.store import IdentityStore
from dequorum.inference.base_model import MockBaseModel, OllamaBaseModel
from dequorum.intake import DuplicateDetector, SubmissionPipeline
from dequorum.knowledge.seeds import populate as populate_seed_contributions
from dequorum.knowledge.store import (
    STATUS_PENDING,
    VALID_STATUSES,
    ContributionStore,
)
from dequorum.review.service import ReviewService
from dequorum.routing import EmbeddingRouter, KeywordRouter
from dequorum.routing.embedder import SentenceTransformerEmbedder
from dequorum.taxonomy.category import Category
from dequorum.taxonomy.seeds import populate as populate_seed_categories


def _resolve_database_url(arg: str | None) -> str:
    """Resolve database URL from CLI arg, env var, or built-in default."""
    return arg or os.environ.get("DEQUORUM_DATABASE_URL") or DEFAULT_DATABASE_URL


def _bootstrap(args: argparse.Namespace) -> str:
    """Set up pool + run migrations. Called by every subcommand. Returns URL."""
    url = _resolve_database_url(getattr(args, "database_url", None))
    init_pool(url)
    upgrade_to_head(url)
    return url


def _ensure_seeded() -> None:
    """Seed each store if empty. Run once after `_bootstrap`."""
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


def _add_database_url_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--database-url",
        default=None,
        help=(
            "Postgres URL. Defaults to $DEQUORUM_DATABASE_URL, then "
            f"{DEFAULT_DATABASE_URL!r}."
        ),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("dequorum")
    sub = parser.add_subparsers(dest="cmd", required=True)

    submit = sub.add_parser(
        "submit", help="Submit a signed contribution (pending review)"
    )
    submit.add_argument(
        "--contributor",
        required=True,
        help="Contributor id (use `dequorum list-contributors`)",
    )
    submit.add_argument(
        "--category",
        required=True,
        help="Primary category id (use `dequorum categories`)",
    )
    submit.add_argument("--text", required=True, help="The factual claim")
    submit.add_argument(
        "--cite",
        action="append",
        default=[],
        help="Citation URL (repeatable, HTTPS only)",
    )
    submit.add_argument(
        "--block-on-duplicate",
        action="store_true",
        help="Hard-fail submission if a likely duplicate exists",
    )
    _add_database_url_arg(submit)

    update = sub.add_parser(
        "update", help="Submit a new version of an existing contribution"
    )
    update.add_argument("--contributor", required=True)
    update.add_argument("--lineage", required=True, help="Lineage id to update")
    update.add_argument("--text", required=True, help="The updated claim text")
    update.add_argument(
        "--cite", action="append", default=[], help="Citation URL (repeatable)"
    )
    update.add_argument(
        "--category",
        default=None,
        help="Optional new primary category (defaults to the existing one)",
    )
    _add_database_url_arg(update)

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
    _add_database_url_arg(signup)

    list_cat = sub.add_parser("categories", help="List the curated category taxonomy")
    _add_database_url_arg(list_cat)

    list_contrib = sub.add_parser(
        "list-contributors", help="List signed-up contributors"
    )
    _add_database_url_arg(list_contrib)

    vote = sub.add_parser("vote", help="Cast a signed vote on a contribution")
    vote.add_argument("--contributor", required=True, help="Voter contributor id")
    vote.add_argument(
        "--contribution", required=True, help="Contribution id (or prefix)"
    )
    vote.add_argument(
        "--score", type=int, required=True, choices=[-1, 0, 1], help="-1, 0, or 1"
    )
    _add_database_url_arg(vote)

    list_c = sub.add_parser(
        "list-contributions", help="List stored contributions with status + tally"
    )
    list_c.add_argument("--category", default=None, help="Filter by category id")
    list_c.add_argument(
        "--status",
        choices=sorted(VALID_STATUSES),
        default=None,
        help="Filter by status",
    )
    _add_database_url_arg(list_c)

    review = sub.add_parser("review", help="Show pending contributions awaiting votes")
    _add_database_url_arg(review)

    serve = sub.add_parser("serve", help="Run the FastAPI web UI")
    serve.add_argument("--host", default="0.0.0.0", help="Bind host")
    serve.add_argument("--port", type=int, default=8000, help="Bind port")
    _add_database_url_arg(serve)
    serve.add_argument("--mock", action="store_true", help="Use mock model")
    serve.add_argument(
        "--router", choices=("keyword", "embedding"), default="embedding"
    )
    serve.add_argument("--min-score", type=float, default=None)
    serve.add_argument("--reload", action="store_true", help="Auto-reload on edits")

    bench = sub.add_parser(
        "benchmark",
        help="Quality check: vanilla vs DeQuorum-full vs DeQuorum-no-retrieval",
    )
    bench.add_argument("--mock", action="store_true", help="Use mock model")
    bench.add_argument(
        "--model",
        default=None,
        help="Model id from inference/models.py registry, or raw Ollama tag.",
    )
    bench.add_argument("--host", default="http://localhost:11434", help="Ollama host")
    bench.add_argument(
        "--router", choices=("keyword", "embedding"), default="embedding"
    )
    bench.add_argument("--min-score", type=float, default=None)
    bench.add_argument("--retrieve-top-k", type=int, default=3)
    _add_database_url_arg(bench)
    bench.add_argument(
        "--output",
        default="docs/benchmarks/report.md",
        help="Where to write the Markdown report",
    )
    bench.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N questions (smoke testing)",
    )

    routebench = sub.add_parser(
        "routebench",
        help="Fast routing-only benchmark (no Ollama). Scales to N=100s.",
    )
    routebench.add_argument(
        "--router", choices=("keyword", "embedding"), default="embedding"
    )
    routebench.add_argument("--min-score", type=float, default=None)
    routebench.add_argument(
        "--per-category",
        type=int,
        default=12,
        help="Template-generated questions per category (default: 12)",
    )
    routebench.add_argument(
        "--seed", type=int, default=42, help="Generator seed for reproducibility"
    )
    routebench.add_argument(
        "--output",
        default="docs/benchmarks/routebench.md",
        help="Where to write the Markdown report",
    )
    _add_database_url_arg(routebench)

    attrib = sub.add_parser(
        "attribution-bench",
        help="Measure leave-one-out contribution attribution vs retrieval score",
    )
    attrib.add_argument("--mock", action="store_true", help="Use mock model")
    attrib.add_argument(
        "--model",
        default=None,
        help="Model id from inference/models.py registry, or raw Ollama tag.",
    )
    attrib.add_argument("--host", default="http://localhost:11434", help="Ollama host")
    attrib.add_argument(
        "--router", choices=("keyword", "embedding"), default="embedding"
    )
    attrib.add_argument("--min-score", type=float, default=None)
    attrib.add_argument("--retrieve-top-k", type=int, default=3)
    attrib.add_argument(
        "--questions",
        choices=("seed", "gold"),
        default="gold",
        help="Question source: 'seed' (15 hand-curated) or 'gold' (all "
        "gold-annotated incl. paraphrase variants — larger faithfulness N)",
    )
    attrib.add_argument(
        "--judge",
        choices=("recall", "llm"),
        default="recall",
        help="Faithfulness judge: 'recall' (gold-fact overlap, deterministic) "
        "or 'llm' (LLM-as-judge — rules out a too-coarse judge as the cause "
        "of a weak correlation)",
    )
    attrib.add_argument(
        "--limit", type=int, default=None, help="Run only the first N questions"
    )
    attrib.add_argument(
        "--output",
        default="docs/benchmarks/attribution.md",
        help="Where to write the Markdown report",
    )
    _add_database_url_arg(attrib)

    distill = sub.add_parser(
        "distill-poc",
        help="Toy LoRA distillation: corpus->weights + leave-one-contributor-out",
    )
    distill.add_argument(
        "--corpus",
        choices=("seed", "novelty"),
        default="seed",
        help="'seed' (peer contributions; needs DB) or 'novelty' (invented "
        "facts the base can't know — DB-free; where a quality gain should show)",
    )
    distill.add_argument(
        "--limit", type=int, default=None, help="First N facts (novelty corpus only)"
    )
    distill.add_argument("--seed", type=int, default=0, help="Random seed")
    distill.add_argument(
        "--base",
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="HuggingFace base model id (small + Apache-2.0 by default)",
    )
    distill.add_argument("--epochs", type=int, default=3)
    distill.add_argument(
        "--router", choices=("keyword", "embedding"), default="embedding"
    )
    distill.add_argument("--min-score", type=float, default=None)
    distill.add_argument("--retrieve-top-k", type=int, default=3)
    distill.add_argument(
        "--target-query",
        default="What protocol does HTTP/3 run on?",
        help="Seeded query whose contributor we leave out for attribution",
    )
    distill.add_argument(
        "--output",
        default="docs/benchmarks/distill.md",
        help="Where to write the Markdown report",
    )
    _add_database_url_arg(distill)

    dattr = sub.add_parser(
        "distill-attribution",
        help="Per-contributor attribution through distillation + gain + "
        "forgetting tax, on the novel-fact corpus (no DB)",
    )
    dattr.add_argument("--base", default="Qwen/Qwen2.5-0.5B-Instruct")
    dattr.add_argument("--epochs", type=int, default=4)
    dattr.add_argument("--limit", type=int, default=None, help="First N facts")
    dattr.add_argument("--seed", type=int, default=0, help="Base random seed")
    dattr.add_argument(
        "--repeats", type=int, default=1, help="Re-run with seed+0..N-1 for mean±range"
    )
    dattr.add_argument("--output", default="docs/benchmarks/distill_attribution.md")

    dcompose = sub.add_parser(
        "distill-compose",
        help="Train two domain adapters on disjoint facts, compose, and test "
        "per-adapter attribution (no DB)",
    )
    dcompose.add_argument("--base", default="Qwen/Qwen2.5-0.5B-Instruct")
    dcompose.add_argument("--epochs", type=int, default=4)
    dcompose.add_argument("--limit", type=int, default=None, help="First N facts")
    dcompose.add_argument("--seed", type=int, default=0, help="Random seed")
    dcompose.add_argument("--output", default="docs/benchmarks/distill_compose.md")

    coverage = sub.add_parser(
        "coverage-bench",
        help="Validate the provenance-coverage meter: base recall on known vs "
        "novel facts (no DB)",
    )
    coverage.add_argument("--mock", action="store_true", help="Use mock model")
    coverage.add_argument("--model", default="", help="Ollama model id/tag")
    coverage.add_argument("--host", default="http://localhost:11434")
    coverage.add_argument("--output", default="docs/benchmarks/coverage.md")

    jbench = sub.add_parser(
        "judge-bench",
        help="Validate the quality judge: does it score correct answers above "
        "plausible-but-wrong ones? (keyword vs LLM judge; no DB)",
    )
    jbench.add_argument("--mock", action="store_true", help="Use mock model")
    jbench.add_argument("--model", default="", help="Ollama model id/tag")
    jbench.add_argument("--host", default="http://localhost:11434")
    jbench.add_argument(
        "--no-llm", action="store_true", help="Keyword judge only (skip the LLM judge)"
    )
    jbench.add_argument("--limit", type=int, default=None, help="First N facts")
    jbench.add_argument("--output", default="docs/benchmarks/judge.md")

    fbench = sub.add_parser(
        "falsehood-bench",
        help="Does grounding on a plausible-but-FALSE contribution make the model "
        "adopt the lie? (no DB)",
    )
    fbench.add_argument("--mock", action="store_true", help="Use mock model")
    fbench.add_argument("--model", default="", help="Ollama model id/tag")
    fbench.add_argument("--host", default="http://localhost:11434")
    fbench.add_argument("--limit", type=int, default=None, help="First N facts")
    fbench.add_argument("--output", default="docs/benchmarks/falsehood.md")

    novelty = sub.add_parser(
        "novelty-bench",
        help="Grounding lift on invented facts the base model can't know (no DB)",
    )
    novelty.add_argument("--mock", action="store_true", help="Use mock model")
    novelty.add_argument(
        "--model", default="", help="Ollama model id/tag (default from registry)"
    )
    novelty.add_argument("--host", default="http://localhost:11434", help="Ollama host")
    novelty.add_argument("--limit", type=int, default=None, help="First N facts only")
    novelty.add_argument(
        "--output",
        default="docs/benchmarks/novelty.md",
        help="Where to write the Markdown report",
    )

    cost = sub.add_parser(
        "cost-model", help="Per-query unit economics + break-even (no DB needed)"
    )
    cost.add_argument("--revenue-per-query", type=float, default=None)
    cost.add_argument("--tokens-out", type=int, default=None)
    cost.add_argument("--usd-per-1m-output", type=float, default=None)
    cost.add_argument("--queries-per-month", type=int, default=None)

    db = sub.add_parser("db", help="Database management commands")
    db_sub = db.add_subparsers(dest="db_cmd", required=True)
    db_upgrade = db_sub.add_parser("upgrade", help="Run Alembic migrations to head")
    _add_database_url_arg(db_upgrade)
    db_seed = db_sub.add_parser("seed", help="Seed all stores from module-level data")
    _add_database_url_arg(db_seed)

    return parser


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
    categories: Sequence[Category], kind: str, min_score: float | None
) -> EmbeddingRouter | KeywordRouter:
    if kind == "embedding":
        embedder = SentenceTransformerEmbedder()
        threshold = 0.30 if min_score is None else min_score
        fallback = KeywordRouter(categories, fallback_to_all=False, min_score=1.0)
        return EmbeddingRouter(
            categories, embedder, min_score=threshold, fallback=fallback
        )
    threshold = 1.0 if min_score is None else min_score
    return KeywordRouter(categories, min_score=threshold)


def _load_contributor(contributor_id: str) -> Contributor | None:
    with open_identity_store() as store:
        for c in store.list_all():
            if c.contributor_id == contributor_id:
                return c
    return None


def _cmd_submit(args: argparse.Namespace) -> int:
    url = _bootstrap(args)
    _ensure_seeded()

    contributor = _load_contributor(args.contributor)
    if contributor is None:
        print(
            json.dumps(
                {"error": f"unknown contributor: {args.contributor!r}"}, indent=2
            )
        )
        return 1
    # Dev path: seed contributors carry a derivable signing key. Real
    # signups pass the key in over a separate channel; we don't try to
    # cover that here.
    from dequorum.identity.seeds import seed_contributor_for

    leaf = args.category.rsplit("/", 1)[-1]
    try:
        _, signing_key = seed_contributor_for(leaf)
    except Exception:
        print(
            json.dumps(
                {"error": "no signing key derivable for this contributor"}, indent=2
            )
        )
        return 1

    embedder = SentenceTransformerEmbedder()
    with (
        open_contribution_store() as store,
        open_category_store() as cat_store,
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
                contributor_signing_key=signing_key,
                text=args.text,
                citations=tuple(args.cite),
                primary_category_id=args.category,
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
                "database_url": url,
            },
            indent=2,
        )
    )
    return 0


def _cmd_update(args: argparse.Namespace) -> int:
    url = _bootstrap(args)
    _ensure_seeded()

    contributor = _load_contributor(args.contributor)
    if contributor is None:
        print(
            json.dumps(
                {"error": f"unknown contributor: {args.contributor!r}"}, indent=2
            )
        )
        return 1

    with (
        open_contribution_store() as store,
        open_category_store() as cat_store,
    ):
        current_contribution = store.current_for_lineage(args.lineage)
        if current_contribution is None:
            existing = store.list_for_lineage(args.lineage)
            if not existing:
                print(
                    json.dumps({"error": f"unknown lineage {args.lineage!r}"}, indent=2)
                )
                return 1
            current_contribution = existing[-1]

        category = args.category or current_contribution.primary_category_id

        from dequorum.identity.seeds import seed_contributor_for

        leaf = category.rsplit("/", 1)[-1]
        try:
            _, signing_key = seed_contributor_for(leaf)
        except Exception:
            print(
                json.dumps(
                    {"error": "no signing key derivable for this contributor"}, indent=2
                )
            )
            return 1

        pipeline = SubmissionPipeline(
            contribution_store=store,
            category_store=cat_store,
            duplicate_detector=None,
        )
        try:
            result = pipeline.submit(
                contributor=contributor,
                contributor_signing_key=signing_key,
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
                "contributor_id": contribution.contributor_id,
                "status": STATUS_PENDING,
                "database_url": url,
            },
            indent=2,
        )
    )
    return 0


def _cmd_signup(args: argparse.Namespace) -> int:
    _bootstrap(args)
    _ensure_seeded()
    import hashlib

    from dequorum.core.crypto import generate_signing_key, public_key_for

    if args.seed_key:
        priv = args.seed_key.encode()
    else:
        priv = generate_signing_key()
    pub = public_key_for(priv)

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

    with open_identity_store() as store:
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
                "private_key_hex": priv.hex(),
                "public_key_hex": contributor.public_key.hex(),
                "store_total": total,
                "warning": (
                    "Save private_key_hex SECURELY. The network cannot recover it."
                ),
            },
            indent=2,
        )
    )
    return 0


def _cmd_list_categories(args: argparse.Namespace) -> int:
    _bootstrap(args)
    _ensure_seeded()
    with open_category_store() as store:
        payload = [
            {
                "category_id": c.category_id,
                "parent_id": c.parent_id,
                "display_name": c.display_name,
                "depth": c.depth,
                "description": c.description,
                "is_routable": c.is_routable,
            }
            for c in store.all()
        ]
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_list_contributors(args: argparse.Namespace) -> int:
    _bootstrap(args)
    _ensure_seeded()
    with open_identity_store() as store:
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
    _bootstrap(args)
    _ensure_seeded()

    with open_contribution_store() as store:
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

        service = ReviewService(store)
        try:
            outcome = service.cast_vote(
                contribution_id=cid, voter_id=args.contributor, score=args.score
            )
        except CompositionError as exc:
            print(json.dumps({"error": str(exc)}, indent=2))
            return 1

    print(json.dumps(asdict(outcome), indent=2))
    return 0


def _cmd_list_contributions(args: argparse.Namespace) -> int:
    _bootstrap(args)
    _ensure_seeded()
    with open_contribution_store() as store:
        if args.category:
            contribs = store.list_by_category(args.category, status=args.status)
        elif args.status:
            contribs = store.list_by_status(args.status)
        else:
            contribs = list(iter(store))
        payload = [
            {
                "contribution_id": c.contribution_id,
                "primary_category_id": c.primary_category_id,
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
    _bootstrap(args)
    _ensure_seeded()
    with open_contribution_store() as store:
        contribs = store.list_by_status(STATUS_PENDING)
        payload = [
            {
                "contribution_id": c.contribution_id,
                "primary_category_id": c.primary_category_id,
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


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from dequorum.web.app import configure_app, create_app

    url = _resolve_database_url(args.database_url)
    configure_app(
        database_url=url,
        use_mock=args.mock,
        router=args.router,
        min_score=args.min_score,
    )
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    _bootstrap(args)
    _ensure_seeded()

    from dequorum.benchmark import SEED_QUESTIONS, run_benchmark
    from dequorum.benchmark.runner import write_markdown_report

    with open_category_store() as cs:
        categories = tuple(cs.routable())

    def router_factory(cats: Sequence[Category]) -> object:
        return _build_router(cats, args.router, args.min_score)

    model: MockBaseModel | OllamaBaseModel = (
        MockBaseModel()
        if args.mock
        else OllamaBaseModel(model=args.model or "", host=args.host)
    )
    if args.mock:
        model_label = "mock"
    else:
        from dequorum.inference.models import DEFAULT_BASE_MODEL_ID, resolve_ollama_tag

        model_label = resolve_ollama_tag(args.model or DEFAULT_BASE_MODEL_ID)

    questions = SEED_QUESTIONS if args.limit is None else SEED_QUESTIONS[: args.limit]

    def progress(i: int, total: int, text: str) -> None:
        print(f"  [{i}/{total}] {text[:80]}", flush=True)

    total = len(questions) * 3
    print(f"Running {len(questions)} questions x 3 conditions = {total} generations...")
    with open_contribution_store() as store:
        report = run_benchmark(
            questions=questions,
            model=model,
            categories=categories,
            store=store,
            router_factory=router_factory,
            retrieve_top_k=args.retrieve_top_k,
            model_label=model_label,
            progress=progress,
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_markdown_report(report, output_path)
    print(f"\nReport written: {output_path}")

    # Quantify Claim 2: judge-score each condition over seeded questions.
    from dequorum.benchmark.runner import score_conditions
    from dequorum.eval import KeywordRecallJudge

    scores = score_conditions(report, KeywordRecallJudge())
    print(
        f"Gold-recall over {scores.n} seeded Q  ·  "
        f"A vanilla={scores.vanilla:.2f}  "
        f"C no-retrieval={scores.dequorum_no_retrieval:.2f}  "
        f"B full={scores.dequorum_full:.2f}"
    )
    return 0


def _cmd_routebench(args: argparse.Namespace) -> int:
    """Fast routing-only benchmark — no Ollama, scales to N=100s."""
    _bootstrap(args)
    _ensure_seeded()

    from dequorum.benchmark.expanded import build_expanded_question_set
    from dequorum.benchmark.routing_only import (
        run_routing_benchmark,
    )
    from dequorum.benchmark.routing_only import (
        write_markdown_report as write_routebench_report,
    )

    with open_category_store() as cs:
        categories = tuple(cs.routable())

    router = _build_router(categories, args.router, args.min_score)
    category_tags = {c.category_id: c.specialty_tags for c in categories}
    questions = build_expanded_question_set(
        category_tags, seed=args.seed, per_category=args.per_category
    )
    print(
        f"Running routebench: {len(questions)} questions, "
        f"router={args.router}, min_score={args.min_score}"
    )
    report = run_routing_benchmark(questions, router=router)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    router_label = type(router).__name__
    write_routebench_report(
        report,
        output_path,
        router_label=router_label,
        routable_category_ids=tuple(c.category_id for c in categories),
    )
    print(f"\nReport written: {output_path}\n")
    print(f"{'BUCKET':<28} {'N':>4} {'ACCEPT':>8} {'MEAN':>6}")
    for bucket in sorted(report.by_bucket):
        s = report.by_bucket[bucket]
        mean = f"{s.mean_score:.2f}" if s.mean_score is not None else "—"
        print(f"{bucket:<28} {s.n:>4} {s.accept_rate * 100:>6.0f}%  {mean:>6}")
    return 0


def _cmd_attribution_bench(args: argparse.Namespace) -> int:
    """Measure leave-one-out contribution attribution across the seed corpus
    and report how well retrieval score predicts measured causal value."""
    _bootstrap(args)
    _ensure_seeded()

    from dequorum.benchmark import SEED_QUESTIONS
    from dequorum.benchmark.attribution import (
        run_attribution_benchmark,
        write_attribution_report,
    )
    from dequorum.eval import KeywordRecallJudge, LLMJudge

    with open_category_store() as cs:
        categories = tuple(cs.routable())
    router = _build_router(categories, args.router, args.min_score)
    embedder = SentenceTransformerEmbedder()

    if args.mock:
        model: MockBaseModel | OllamaBaseModel = MockBaseModel()
        model_label = "mock"
    else:
        from dequorum.inference.models import DEFAULT_BASE_MODEL_ID, resolve_ollama_tag

        # Shorter generations + a generous timeout: the attribution measure
        # only needs the answer's content, and CPU inference of (k+1)
        # generations per query is slow.
        model = OllamaBaseModel(
            model=args.model or "",
            host=args.host,
            timeout_seconds=300.0,
            num_predict=192,
        )
        model_label = resolve_ollama_tag(args.model or DEFAULT_BASE_MODEL_ID)

    judge = LLMJudge(model) if args.judge == "llm" else KeywordRecallJudge()

    if args.questions == "gold":
        from dequorum.eval import gold_questions

        source: list = gold_questions()
    else:
        source = list(SEED_QUESTIONS)
    questions = source if args.limit is None else source[: args.limit]

    def progress(i: int, total: int, text: str) -> None:
        print(f"  [{i}/{total}] {text[:80]}", flush=True)

    print(f"Running attribution-bench over {len(questions)} questions...")
    with open_contribution_store() as store:
        report = run_attribution_benchmark(
            questions=questions,
            router=router,
            store=store,
            model=model,
            embedder=embedder,
            judge=judge,
            retrieve_top_k=args.retrieve_top_k,
            progress=progress,
        )
    report.model_label = model_label

    output_path = Path(args.output)
    write_attribution_report(report, output_path)
    print(f"\nReport written: {output_path}")
    print(
        f"queries={len(report.rows)} pairs={report.n_pairs} "
        f"spearman(score,value)={report.spearman_score_vs_value:.3f}"
    )
    return 0


def _cmd_distill_poc(args: argparse.Namespace) -> int:
    """Toy LoRA distillation: show the corpus moves into the weights, and
    that leaving one contributor's examples out removes exactly their fact."""
    from dequorum.distill import attribution_delta, exclude_contributor
    from dequorum.distill.poc import (
        TrainingExample,
        base_generator,
        generate,
        seed_everything,
        train_lora,
    )
    from dequorum.eval import KeywordRecallJudge

    seed_everything(getattr(args, "seed", 0))
    judge = KeywordRecallJudge()
    corpus = getattr(args, "corpus", "seed")

    if corpus == "novelty":
        # Invented facts the base model cannot know — distilling these is where
        # a *quality* gain (not just attribution) should appear. No DB needed.
        from dequorum.benchmark.novelty import NOVELTY_FACTS

        facts = NOVELTY_FACTS if args.limit is None else NOVELTY_FACTS[: args.limit]
        all_examples = [
            TrainingExample(
                prompt=f.query,
                completion=f.note,
                contributor_id=f"dq:novelty-{i}",
                contribution_id=f"nov-{i}",
            )
            for i, f in enumerate(facts)
        ]
        recall_items = [(f.query, f.gold) for f in facts]
        target_query, target_gold = facts[0].query, facts[0].gold
        target_contributor = "dq:novelty-0"
        corpus_label = f"novelty ({len(facts)} invented facts)"
    else:
        _bootstrap(args)
        _ensure_seeded()
        from dequorum.benchmark import SEED_QUESTIONS
        from dequorum.distill import build_examples
        from dequorum.eval import gold_for
        from dequorum.retrieval import Retriever

        with open_category_store() as cs:
            categories = tuple(cs.routable())
        router = _build_router(categories, args.router, args.min_score)
        seeded = [q for q in SEED_QUESTIONS if gold_for(q.text)]
        all_examples = []
        target_contributor = None
        with open_contribution_store() as store:
            retriever = Retriever(store)
            for q in seeded:
                routing = router.route(q.text, top_k=1)
                if not routing.selected:
                    continue
                cat = routing.selected[0].category
                retrieved = tuple(
                    retriever.retrieve(
                        q.text, cat.category_id, top_k=args.retrieve_top_k
                    )
                )
                all_examples.extend(build_examples(q.text, retrieved))
                if q.text == args.target_query and retrieved:
                    target_contributor = retrieved[0].contribution.contributor_id
        if not all_examples or target_contributor is None:
            print("No training examples / target not grounded — is the corpus seeded?")
            return 1
        recall_items = [(q.text, gold_for(q.text)) for q in seeded]
        target_query, target_gold = args.target_query, gold_for(args.target_query)
        corpus_label = f"seed ({len(seeded)} seeded queries)"

    minus_examples = exclude_contributor(all_examples, target_contributor)
    print(
        f"Examples: {len(all_examples)} (minus target: {len(minus_examples)}) · "
        f"base={args.base} · corpus={corpus} · target contributor={target_contributor}"
    )

    def mean_recall(gen) -> float:
        vals = [
            judge.score(query=q, answer=gen(q), reference=g) for q, g in recall_items
        ]
        return sum(vals) / len(vals)

    def target_recall(gen) -> float:
        return judge.score(
            query=target_query, answer=gen(target_query), reference=target_gold
        )

    print("Baseline (no adapter)...")
    base_gen = base_generator(args.base)
    base_mean, base_target = mean_recall(base_gen), target_recall(base_gen)

    print("Training LoRA on full corpus...")
    m_all, t_all = train_lora(all_examples, base_id=args.base, epochs=args.epochs)
    all_mean = mean_recall(lambda p: generate(m_all, t_all, p))
    all_target = target_recall(lambda p: generate(m_all, t_all, p))

    print("Training LoRA without target contributor...")
    m_minus, t_minus = train_lora(minus_examples, base_id=args.base, epochs=args.epochs)
    minus_target = target_recall(lambda p: generate(m_minus, t_minus, p))

    delta = attribution_delta(
        recall_with=all_target, recall_without=minus_target, recall_base=base_target
    )
    lines = [
        "# Distillation PoC",
        "",
        f"Base: `{args.base}` · epochs {args.epochs} · corpus {corpus_label}",
        "",
        "## Corpus → weights (retrieval-suppressed gold recall)",
        "",
        f"- mean recall, base model: {base_mean:.3f}",
        f"- mean recall, LoRA on full corpus: {all_mean:.3f}",
        f"- **learned gain: {all_mean - base_mean:+.3f}**",
        "",
        "## Attribution survives distillation",
        "",
        f"Target: '{args.target_query}' · contributor `{target_contributor}`",
        "",
        f"- recall, base: {base_target:.3f}",
        f"- recall, LoRA-all: {all_target:.3f}",
        f"- recall, LoRA-without-contributor: {minus_target:.3f}",
        f"- **attributable fraction: {delta['attributable_fraction']:.3f}** — share of "
        "the learned fact traceable to this contributor's examples via "
        "leave-one-contributor-out.",
        "",
    ]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"\nReport written: {out}")
    print(
        f"learned_gain(mean)={all_mean - base_mean:+.3f}  "
        f"target_attributable={delta['attributable_fraction']:.3f}"
    )
    return 0


def _cmd_distill_attribution(args: argparse.Namespace) -> int:
    """E1+E2+E3: per-contributor attribution through distillation, knowledge
    gain, and the forgetting tax — on the novel-fact corpus (no DB)."""
    import gc

    import torch

    from dequorum.benchmark.novelty import NOVELTY_FACTS
    from dequorum.benchmark.questions import SEED_QUESTIONS
    from dequorum.distill import (
        TrainingExample,
        attributable_fraction,
        entanglement_score,
        forgetting_tax,
        knowledge_gain,
    )
    from dequorum.distill.poc import (
        base_generator,
        generate,
        seed_everything,
        train_lora,
    )
    from dequorum.eval import KeywordRecallJudge, gold_for

    judge = KeywordRecallJudge()
    facts = NOVELTY_FACTS if args.limit is None else NOVELTY_FACTS[: args.limit]
    examples = [
        TrainingExample(
            prompt=f.query,
            completion=f.note,
            contributor_id=f"dq:nov-{i}",
            contribution_id=f"nov-{i}",
        )
        for i, f in enumerate(facts)
    ]
    nov_items = [(f.query, f.gold) for f in facts]
    # Held-out paraphrases (never trained on) — recall here vs on the training
    # query separates real knowledge transfer from memorizing the prompt.
    para_items = [(f.paraphrase, f.gold) for f in facts]
    # Control = facts the base already knows (seeded), to measure forgetting.
    control = [(q.text, gold_for(q.text)) for q in SEED_QUESTIONS if gold_for(q.text)]

    def recall(gen, items) -> list[float]:
        return [judge.score(query=q, answer=gen(q), reference=g) for q, g in items]

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    def free_cuda() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def train_and_recall(ex, with_para: bool = False):
        """Train a LoRA and measure recall. Model is local → freed on return."""
        m, t = train_lora(ex, base_id=args.base, epochs=args.epochs)
        nov = recall(lambda p: generate(m, t, p), nov_items)
        ctrl = recall(lambda p: generate(m, t, p), control)
        para = recall(lambda p: generate(m, t, p), para_items) if with_para else []
        return nov, ctrl, para

    def run_once(seed: int) -> dict:
        seed_everything(seed)
        print(f"  [seed {seed}] baseline...")
        bg = base_generator(args.base)
        base_nov = recall(bg, nov_items)
        base_ctrl = recall(bg, control)
        del bg
        free_cuda()
        print(f"  [seed {seed}] training on full corpus...")
        all_nov, all_ctrl, all_para = train_and_recall(examples, with_para=True)
        free_cuda()
        minus: list[list[float]] = []
        for i in range(len(facts)):
            print(f"  [seed {seed}] minus contributor {i + 1}/{len(facts)}...")
            ex_i = [e for e in examples if e.contributor_id != f"dq:nov-{i}"]
            nov_i, _, _ = train_and_recall(ex_i)
            minus.append(nov_i)
            free_cuda()
        attrib = [
            attributable_fraction(
                base=base_nov[j], with_all=all_nov[j], without_own=minus[j][j]
            )
            for j in range(len(facts))
        ]
        return {
            "base_nov": base_nov,
            "all_nov": all_nov,
            "minus": minus,
            "attrib": attrib,
            "gain": knowledge_gain(base_nov, all_nov),
            "mean_attrib": mean(attrib),
            "entanglement": entanglement_score(all_nov, minus),
            "forget": forgetting_tax(base_ctrl, all_ctrl),
            "canonical": mean(all_nov),
            "paraphrase": mean(all_para),
            "base_ctrl": mean(base_ctrl),
            "all_ctrl": mean(all_ctrl),
        }

    runs = [run_once(args.seed + r) for r in range(args.repeats)]
    r0 = runs[0]

    def agg(key: str) -> str:
        vals = [r[key] for r in runs]
        if len(vals) == 1:
            return f"{vals[0]:+.3f}" if vals[0] < 0 else f"{vals[0]:.3f}"
        return f"{mean(vals):.3f}  [min {min(vals):.3f}, max {max(vals):.3f}]"

    lines = [
        "# Distillation: attribution, gain, forgetting, and memorization",
        "",
        f"Base: `{args.base}` · epochs {args.epochs} · facts {len(facts)} · "
        f"seed {args.seed} · repeats {args.repeats}",
        "",
        "## Headline metrics"
        + (f" (mean over {args.repeats} seeds)" if args.repeats > 1 else ""),
        "",
        f"- **knowledge gain (E2):** {agg('gain')}",
        f"- **mean attributable fraction (E1):** {agg('mean_attrib')}",
        f"- **entanglement (E1, ≈0 is good):** {agg('entanglement')}",
        f"- **forgetting tax (E3):** {agg('forget')}",
        f"- **memorization check — trained-query recall:** {agg('canonical')}",
        f"- **memorization check — held-out paraphrase recall:** {agg('paraphrase')} "
        "(close to trained-query ⇒ real knowledge, not prompt memorization)",
        "",
        f"## Per-contributor attribution (E1) — seed {args.seed}",
        "",
        "| fact | base | trained | trained-minus-own | attributable |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for j in range(len(facts)):
        lines.append(
            f"| {j} | {r0['base_nov'][j]:.2f} | {r0['all_nov'][j]:.2f} | "
            f"{r0['minus'][j][j]:.2f} | {r0['attrib'][j]:.2f} |"
        )
    lines += [
        "",
        "Entanglement ≈ 0 means removing one contributor leaves the others' "
        "knowledge intact — the property required for certifiable ownership. The "
        "forgetting tax is the change in recall on base-known facts after training; "
        "negative means owning the corpus degraded unrelated knowledge.",
        "",
    ]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"\nReport written: {out}")
    print(
        f"gain={agg('gain')}  attributable={agg('mean_attrib')}  "
        f"entanglement={agg('entanglement')}  forgetting={agg('forget')}  "
        f"paraphrase={agg('paraphrase')}"
    )
    return 0


def _cmd_distill_compose(args: argparse.Namespace) -> int:
    """E4: train two domain adapters on disjoint fact sets, compose them, and
    check both knowledge sets are present and each remains attributable."""
    import tempfile

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from dequorum.benchmark.novelty import NOVELTY_FACTS
    from dequorum.distill.poc import (
        TrainingExample,
        generate,
        seed_everything,
        train_lora,
    )
    from dequorum.eval import KeywordRecallJudge

    seed_everything(getattr(args, "seed", 0))

    judge = KeywordRecallJudge()
    facts = NOVELTY_FACTS if args.limit is None else NOVELTY_FACTS[: args.limit]
    half = len(facts) // 2
    groups = {"A": list(enumerate(facts))[:half], "B": list(enumerate(facts))[half:]}

    def examples_for(group) -> list[TrainingExample]:
        return [
            TrainingExample(
                prompt=f.query,
                completion=f.note,
                contributor_id=f"dq:nov-{i}",
                contribution_id=f"nov-{i}",
            )
            for i, f in group
        ]

    tmp = tempfile.mkdtemp()
    for name in ("A", "B"):
        print(f"Training adapter {name}...")
        m, _ = train_lora(
            examples_for(groups[name]), base_id=args.base, epochs=args.epochs
        )
        m.save_pretrained(f"{tmp}/{name}")
        del m
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    device = "cuda" if torch.cuda.is_available() else "cpu"
    base = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.float32)
    base.to(device)
    model = PeftModel.from_pretrained(base, f"{tmp}/A", adapter_name="A")
    model.load_adapter(f"{tmp}/B", adapter_name="B")

    def recall_group(group) -> float:
        vals = [
            judge.score(
                query=f.query, answer=generate(model, tok, f.query), reference=f.gold
            )
            for _, f in group
        ]
        return sum(vals) / len(vals) if vals else 0.0

    model.set_adapter(["A", "B"])
    both_a, both_b = recall_group(groups["A"]), recall_group(groups["B"])
    model.set_adapter(["A"])  # ablate B
    ablate_a, ablate_b = recall_group(groups["A"]), recall_group(groups["B"])

    lines = [
        "# Distillation: adapter composition (E4)",
        "",
        f"Base: `{args.base}` · epochs {args.epochs} · "
        f"adapter A facts {len(groups['A'])} · adapter B facts {len(groups['B'])}",
        "",
        "| condition | recall(A facts) | recall(B facts) |",
        "| --- | ---: | ---: |",
        f"| A+B composed | {both_a:.2f} | {both_b:.2f} |",
        f"| A only (B ablated) | {ablate_a:.2f} | {ablate_b:.2f} |",
        "",
        "Composition holds if A+B recalls both sets; per-adapter attribution "
        "holds if ablating B drops B's facts while leaving A's intact.",
        "",
    ]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"\nReport written: {out}")
    print(
        f"composed A={both_a:.2f} B={both_b:.2f} · ablate-B -> A={ablate_a:.2f} "
        f"B={ablate_b:.2f}"
    )
    return 0


def _cmd_coverage_bench(args: argparse.Namespace) -> int:
    """E6: validate the provenance-coverage instrument — base recall should be
    high on base-known facts and low on novel facts (no training, no DB)."""
    from dequorum.benchmark.novelty import NOVELTY_FACTS
    from dequorum.benchmark.questions import SEED_QUESTIONS
    from dequorum.eval import KeywordRecallJudge, gold_for
    from dequorum.inference.base_model import MockBaseModel, OllamaBaseModel
    from dequorum.inference.models import DEFAULT_BASE_MODEL_ID, resolve_ollama_tag

    judge = KeywordRecallJudge()
    if args.mock:
        model: object = MockBaseModel()
        label = "mock"
    else:
        model = OllamaBaseModel(
            model=args.model, host=args.host, timeout_seconds=300.0, num_predict=192
        )
        label = resolve_ollama_tag(args.model or DEFAULT_BASE_MODEL_ID)

    system = "You are a precise assistant. Answer the question concisely."

    def base_recall(items) -> float:
        vals = [
            judge.score(
                query=q,
                answer=model.complete(system=system, user=q),  # type: ignore[attr-defined]
                reference=g,
            )
            for q, g in items
        ]
        return sum(vals) / len(vals) if vals else 0.0

    known = [(q.text, gold_for(q.text)) for q in SEED_QUESTIONS if gold_for(q.text)]
    novel = [(f.query, f.gold) for f in NOVELTY_FACTS]
    known_cov, novel_cov = base_recall(known), base_recall(novel)

    lines = [
        "# Provenance-coverage instrument (E6)",
        "",
        f"Model: `{label}`",
        "",
        "The instrument measures whether the base model already knows a fact "
        "(high base recall ⇒ the base covers it; low ⇒ only the commons can). "
        "It is valid if it separates known from novel facts.",
        "",
        f"- mean base recall, **base-known facts** (n={len(known)}): {known_cov:.3f}",
        f"- mean base recall, **novel facts** (n={len(novel)}): {novel_cov:.3f}",
        f"- **separation: {known_cov - novel_cov:+.3f}** "
        "(large ⇒ the meter reliably tells borrowed knowledge from commons-only)",
        "",
    ]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"\nReport written: {out}")
    print(
        f"known={known_cov:.3f}  novel={novel_cov:.3f}  sep={known_cov - novel_cov:+.3f}"
    )
    return 0


def _cmd_novelty_bench(args: argparse.Namespace) -> int:
    """Grounding lift on invented facts; needs only a model (no DB)."""
    from dequorum.benchmark.novelty import (
        NOVELTY_FACTS,
        run_novelty_benchmark,
        write_novelty_report,
    )
    from dequorum.inference.base_model import MockBaseModel, OllamaBaseModel
    from dequorum.inference.models import DEFAULT_BASE_MODEL_ID, resolve_ollama_tag

    if args.mock:
        model: object = MockBaseModel()
        label = "mock"
    else:
        model = OllamaBaseModel(
            model=args.model, host=args.host, timeout_seconds=300.0, num_predict=192
        )
        label = resolve_ollama_tag(args.model or DEFAULT_BASE_MODEL_ID)

    facts = NOVELTY_FACTS if args.limit is None else NOVELTY_FACTS[: args.limit]

    def progress(i: int, total: int, text: str) -> None:
        print(f"  [{i}/{total}] {text[:80]}", flush=True)

    print(f"Running novelty-bench over {len(facts)} invented facts...")
    report = run_novelty_benchmark(model, facts=facts, progress=progress)  # type: ignore[arg-type]
    report.model_label = label
    write_novelty_report(report, args.output)
    print(
        f"base={report.mean_base:.3f}  grounded={report.mean_grounded:.3f}  "
        f"lift={report.lift:+.3f}"
    )
    print(f"Report written: {args.output}")
    return 0


def _judge_bench_model(args: argparse.Namespace):
    from dequorum.inference.base_model import MockBaseModel, OllamaBaseModel

    if args.mock:
        return MockBaseModel()
    return OllamaBaseModel(
        model=args.model, host=args.host, timeout_seconds=300.0, num_predict=64
    )


def _cmd_judge_bench(args: argparse.Namespace) -> int:
    """Validate the quality judge: score known-correct answers (the note) vs
    plausible-but-wrong answers (the false note) against the true gold. A good
    judge separates them; a coarse one over-credits the wrong answer."""
    from dequorum.benchmark.novelty import NOVELTY_FACTS
    from dequorum.eval import KeywordRecallJudge, LLMJudge

    facts = NOVELTY_FACTS if args.limit is None else NOVELTY_FACTS[: args.limit]

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    judges: dict[str, object] = {"keyword": KeywordRecallJudge()}
    if not args.no_llm:
        judges["llm"] = LLMJudge(_judge_bench_model(args))

    lines = [
        "# Judge validation",
        "",
        f"Facts: {len(facts)}. Each judge scores a correct answer (the fact's "
        "note) and a plausible-but-wrong answer (a false variant) against the "
        "true gold. Separation and pairwise accuracy measure how trustworthy the "
        "judge is; the keyword judge is expected to over-credit the wrong answer "
        "because it matches structural tokens.",
        "",
        "| judge | mean(correct) | mean(wrong) | separation | pairwise acc |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    summary = {}
    for name, judge in judges.items():
        correct = [
            judge.score(query=f.query, answer=f.note, reference=f.gold)  # type: ignore[attr-defined]
            for f in facts
        ]
        wrong = [
            judge.score(query=f.query, answer=f.false_note, reference=f.gold)  # type: ignore[attr-defined]
            for f in facts
        ]
        pair = mean(
            [1.0 if c > w else (0.5 if c == w else 0.0) for c, w in zip(correct, wrong)]
        )
        sep = mean(correct) - mean(wrong)
        summary[name] = (sep, pair)
        lines.append(
            f"| {name} | {mean(correct):.3f} | {mean(wrong):.3f} | "
            f"{sep:+.3f} | {pair:.3f} |"
        )
    lines += [
        "",
        "Higher separation and pairwise accuracy mean a more trustworthy judge. "
        "A near-zero or negative separation means the judge cannot tell correct "
        "from plausibly-wrong, and any quality number measured with it is suspect.",
        "",
    ]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"Report written: {out}")
    for name, (sep, pair) in summary.items():
        print(f"{name}: separation={sep:+.3f} pairwise_acc={pair:.3f}")
    return 0


def _cmd_falsehood_bench(args: argparse.Namespace) -> int:
    """Does grounding on a plausible-but-FALSE contribution make the model adopt
    the lie? Grounds on each fact's false variant and measures how often the
    answer states the false claim — i.e. whether grounding propagates falsehood."""
    from dequorum.benchmark.novelty import _BASE_SYSTEM, _GROUNDED_SYSTEM, NOVELTY_FACTS
    from dequorum.eval import KeywordRecallJudge

    facts = NOVELTY_FACTS if args.limit is None else NOVELTY_FACTS[: args.limit]
    judge = KeywordRecallJudge()
    model = _judge_bench_model(args)

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    base_false, adopt_false, keep_true = [], [], []
    for i, f in enumerate(facts):
        print(f"  [{i + 1}/{len(facts)}] {f.query[:70]}", flush=True)
        base_ans = model.complete(system=_BASE_SYSTEM, user=f.query)
        grounded = model.complete(
            system=_GROUNDED_SYSTEM.format(note=f.false_note), user=f.query
        )
        base_false.append(
            judge.score(query=f.query, answer=base_ans, reference=f.false_gold)
        )
        adopt_false.append(
            judge.score(query=f.query, answer=grounded, reference=f.false_gold)
        )
        keep_true.append(judge.score(query=f.query, answer=grounded, reference=f.gold))

    lines = [
        "# Falsehood propagation",
        "",
        f"Facts: {len(facts)}. Each is grounded on a plausible-but-FALSE variant of "
        "the contribution; we measure whether the answer adopts the false claim.",
        "",
        f"- base model, false claim recall (control, expect ~0): {mean(base_false):.3f}",
        f"- **grounded-on-false, false claim recall: {mean(adopt_false):.3f}** "
        "(high ⇒ the model adopts the lie)",
        f"- grounded-on-false, true claim recall: {mean(keep_true):.3f}",
        "",
        "If grounded-on-false recall is high, grounding faithfully propagates "
        "whatever the contribution asserts, true or false. Correctness therefore "
        "rests entirely on the governance layer (review + voting) filtering false "
        "contributions before they ground answers — the model provides no defense.",
        "",
        "| fact | base (false) | grounded (false) | grounded (true) |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for i in range(len(facts)):
        lines.append(
            f"| {i} | {base_false[i]:.2f} | {adopt_false[i]:.2f} | {keep_true[i]:.2f} |"
        )
    lines.append("")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"Report written: {out}")
    print(
        f"base_false={mean(base_false):.3f}  adopt_false={mean(adopt_false):.3f}  "
        f"keep_true={mean(keep_true):.3f}"
    )
    return 0


def _cmd_cost_model(args: argparse.Namespace) -> int:
    """Print per-query unit economics; no database or model required."""
    from dequorum.economics import CostModel

    overrides = {}
    if args.revenue_per_query is not None:
        overrides["revenue_per_query"] = args.revenue_per_query
    if args.tokens_out is not None:
        overrides["tokens_out"] = args.tokens_out
    if args.usd_per_1m_output is not None:
        overrides["usd_per_1m_output"] = args.usd_per_1m_output
    if args.queries_per_month is not None:
        overrides["queries_per_month"] = args.queries_per_month
    model = CostModel(**overrides)
    for line in model.report_lines():
        print(line)
    return 0


def _cmd_db(args: argparse.Namespace) -> int:
    url = _resolve_database_url(args.database_url)
    if args.db_cmd == "upgrade":
        init_pool(url)
        upgrade_to_head(url)
        print(json.dumps({"ok": True, "database_url": url, "action": "upgrade"}))
        return 0
    if args.db_cmd == "seed":
        init_pool(url)
        upgrade_to_head(url)
        _ensure_seeded()
        with open_contribution_store() as cstore, open_identity_store() as istore:
            totals = {
                "contributions": len(cstore),
                "contributors": len(istore),
            }
        print(json.dumps({"ok": True, "database_url": url, "totals": totals}))
        return 0
    return 2


# Re-exported for tests / external scripts that import from dequorum.cli.
_ = IdentityStore


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
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
    if args.cmd == "serve":
        return _cmd_serve(args)
    if args.cmd == "benchmark":
        return _cmd_benchmark(args)
    if args.cmd == "routebench":
        return _cmd_routebench(args)
    if args.cmd == "attribution-bench":
        return _cmd_attribution_bench(args)
    if args.cmd == "distill-poc":
        return _cmd_distill_poc(args)
    if args.cmd == "distill-attribution":
        return _cmd_distill_attribution(args)
    if args.cmd == "distill-compose":
        return _cmd_distill_compose(args)
    if args.cmd == "coverage-bench":
        return _cmd_coverage_bench(args)
    if args.cmd == "judge-bench":
        return _cmd_judge_bench(args)
    if args.cmd == "falsehood-bench":
        return _cmd_falsehood_bench(args)
    if args.cmd == "cost-model":
        return _cmd_cost_model(args)
    if args.cmd == "novelty-bench":
        return _cmd_novelty_bench(args)
    if args.cmd == "db":
        return _cmd_db(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
