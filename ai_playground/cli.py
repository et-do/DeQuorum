"""Command-line entry point exposed by [project.scripts] in pyproject."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict

from ai_playground.core.errors import CompositionError
from ai_playground.core.ledger import AttributionLedger
from ai_playground.expert_network.pipeline import diagnose


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai_playground")
    sub = parser.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo", help="Run the toy expert-network pipeline")
    demo.add_argument("--symptom", default="fatigue")
    demo.add_argument("--age", type=int, default=14)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.cmd == "demo":
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

    return 2


if __name__ == "__main__":
    sys.exit(main())
