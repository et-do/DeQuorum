"""Command-line entry point exposed by [project.scripts] in pyproject."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from ai_playground.base_model import MockBaseModel, OllamaBaseModel
from ai_playground.contribution_store import ContributionStore
from ai_playground.contributions import Contribution
from ai_playground.core.errors import CompositionError
from ai_playground.core.ledger import AttributionLedger
from ai_playground.expert_network.pipeline import diagnose
from ai_playground.pipeline import Pipeline
from ai_playground.retrieval import Retriever
from ai_playground.router import KeywordRouter
from ai_playground.seed_contributions import populate as populate_seed_contributions
from ai_playground.seed_experts import build_seed_registry

DEFAULT_DB = "./.ai_playground.db"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai_playground")
    sub = parser.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo", help="Run the toy expert-network pipeline")
    demo.add_argument("--symptom", default="fatigue")
    demo.add_argument("--age", type=int, default=14)

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
    query.add_argument("--db", default=DEFAULT_DB, help="Contribution DB path")

    submit = sub.add_parser("submit", help="Submit a signed contribution")
    submit.add_argument("--as", dest="expert_id", required=True, help="Expert id")
    submit.add_argument("--text", required=True, help="The factual claim")
    submit.add_argument(
        "--cite", action="append", default=[], help="Citation URL (repeatable)"
    )
    submit.add_argument("--db", default=DEFAULT_DB)

    list_c = sub.add_parser(
        "list-contributions", help="List stored contributions, optionally filtered"
    )
    list_c.add_argument("--expert", default=None, help="Filter by expert id")
    list_c.add_argument("--db", default=DEFAULT_DB)

    sub.add_parser("list-experts", help="Print the seed expert registry")

    return parser


def _open_store(path: str) -> ContributionStore:
    """Open the store at path and seed it on first use if empty."""
    is_new = path == ":memory:" or not Path(path).exists()
    store = ContributionStore(path)
    if is_new and len(store) == 0:
        populate_seed_contributions(store)
    return store


def _cmd_demo(args: argparse.Namespace) -> int:
    try:
        proof = diagnose(args.symptom, args.age)
    except CompositionError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1
    ledger = AttributionLedger()
    ledger.credit(proof)
    print(
        json.dumps(
            {
                "output": proof.output,
                "chain": [asdict(sig) for sig in proof.chain],
                "ledger": ledger.totals(),
            },
            indent=2,
        )
    )
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    registry = build_seed_registry()
    router = KeywordRouter(registry)
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
            "selected": [e.expert_id for e in response.routing.selected],
        },
        "experts": [
            {
                "expert_id": a.expert.expert_id,
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
        store.add(contribution)
        total = len(store)

    print(
        json.dumps(
            {
                "contribution_id": contribution.contribution_id,
                "expert_id": contribution.expert_id,
                "signature": asdict(contribution.signature),
                "store_total": total,
                "db": args.db,
            },
            indent=2,
        )
    )
    return 0


def _cmd_list_contributions(args: argparse.Namespace) -> int:
    with _open_store(args.db) as store:
        contribs = (
            store.list_for_expert(args.expert) if args.expert else list(iter(store))
        )
        payload = [
            {
                "contribution_id": c.contribution_id,
                "expert_id": c.expert_id,
                "contributor_id": c.contributor_id,
                "text": c.text,
                "citations": list(c.citations),
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


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "demo":
        return _cmd_demo(args)
    if args.cmd == "query":
        return _cmd_query(args)
    if args.cmd == "submit":
        return _cmd_submit(args)
    if args.cmd == "list-contributions":
        return _cmd_list_contributions(args)
    if args.cmd == "list-experts":
        return _cmd_list_experts(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
