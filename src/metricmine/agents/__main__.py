"""CLI: propose silver | propose mapping (D-24).

Spec: docs/spec/agent-layer.md §4. The interaction surface is the CLI,
the editor, and the pull request; this module is the CLI half of
propose. It refuses to run without the stance's prompt file (the prompt
PR lands the bodies) and honors the D-34 model override via --model.
`--help` works keyless; no client is constructed before the harness
preconditions pass.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from metricmine.agents import eval as eval_lane
from metricmine.agents import harness, mapping_proposer, silver_proposer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m metricmine.agents",
        description=(
            "Run a proposer against the newest committed profile artifact "
            "and write a draft contract plus its record to the gitignored "
            "proposals/ outbox (D-24: merge is approval)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose = subparsers.add_parser(
        "propose", help="run one proposer, one structured call (D-21)"
    )
    propose.add_argument(
        "proposer",
        choices=["silver", "mapping"],
        help="silver: cleanup stance over the bronze profile; "
        "mapping: propose stance over the silver profile",
    )
    propose.add_argument(
        "--profile",
        default=None,
        help="explicit profile artifact path (default: the newest vNNNN)",
    )
    propose.add_argument(
        "--model",
        default=None,
        help="allow-listed model ID override (D-34); precedence "
        "--model, then MM_PROPOSER_MODEL, then the pinned default",
    )
    evaluate = subparsers.add_parser(
        "eval",
        help="the live eval lane over the golden-profile set (D-25); "
        "needs a key",
    )
    evaluate.add_argument(
        "--model",
        default=None,
        help="allow-listed model ID override (D-34), the same precedence "
        "as propose",
    )
    evaluate.add_argument(
        "--fixture",
        action="append",
        default=None,
        metavar="LABEL",
        help="run only the named fixture label(s) from agents.eval.fixtures",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[3]
    if args.command == "eval":
        return eval_lane.run_eval(
            repo_root, model_flag=args.model, labels=args.fixture
        )
    build = (
        silver_proposer.build_spec
        if args.proposer == "silver"
        else mapping_proposer.build_spec
    )
    spec = build(repo_root)
    return harness.run_proposer(
        spec, repo_root, profile=args.profile, model_flag=args.model
    )


if __name__ == "__main__":
    sys.exit(main())
