"""CLI for the deterministic adoption tools (D-35).

`scan`, `verify-grain`, and `enforce-properties` are deterministic code,
never agents (D-10 Amendment G, CLAUDE.md rule 15): no model call, no
network, no loop. The proposers stay the only LLM surface. This is a
CLI, not the stdio server: stdout carries results and stderr
diagnostics (rule 18's stdout discipline governs src/metricmine/server/
only).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from metricmine.adoption import enforce_properties, scan, verify_grain


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m metricmine.adoption",
        description=(
            "Deterministic adoption tools over the model tree and the "
            "read-only warehouse (D-35): never agents, never writers of "
            "contracts or models."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "scan",
        help="derive the review queue from the tree and the read-only "
        "warehouse; write plan.md and plan.json to the outbox (D-35)",
    )

    grain = subparsers.add_parser(
        "verify-grain",
        help="measure a declared grain against the live warehouse (F-10)",
    )
    grain.add_argument("--table", required=True)
    grain.add_argument(
        "--keys",
        required=True,
        help="comma-separated column names, the declared grain tuple",
    )
    grain.add_argument("--schema", default="silver")

    enforce = subparsers.add_parser(
        "enforce-properties",
        help="add the two enforcement keys the approved contract implies "
        "(D-16 Amendment J)",
    )
    enforce.add_argument("--table", required=True)

    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[3]
    if args.command == "scan":
        return scan.run(repo_root)
    if args.command == "verify-grain":
        keys = [key.strip() for key in args.keys.split(",") if key.strip()]
        return verify_grain.run(repo_root, args.table, keys, schema=args.schema)
    return enforce_properties.run(repo_root, args.table)


if __name__ == "__main__":
    sys.exit(main())
