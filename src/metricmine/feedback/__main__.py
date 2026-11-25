"""The command door: the same code as the server's prepare_feedback tool,
for anyone with the repository and no agent at all.

    python -m metricmine.feedback prepare --field invoice_lines.quantity --kind rule_wanted \\
        --claim "..." --query "select * from gold.mart_invoice_lines_typed where ..." [--db <served file>] [--out <file>]
    python -m metricmine.feedback verify --build <warehouse.duckdb> --message <file> \\
        [--key-field <category>.<column>] [--key-kind <kind>] [--key-count <n>] [--json <out>]

prepare prints the message (and writes it to --out when asked, the one
write a person requests); verify prints its measurement lines. The
served file for prepare resolves as the server does: MM_SERVE_DB, then
demo/demo.duckdb, or --db. Exit 0 whenever a command ran; a refused
prepare prints REFUSED with the reason and the remedy and exits 2.
"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

from metricmine.query import GoldWarehouse

from .prepare import FeedbackRefused, prepare, render
from .verify import print_report, report_json, verify


def _version() -> str:
    try:
        return package_version("metricmine")
    except PackageNotFoundError:  # pragma: no cover
        return "0.0.0"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m metricmine.feedback", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="render the five-part message from the served file; writes nothing unless --out")
    p.add_argument("--field", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--claim", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--db", default=None, help="the served file (default: MM_SERVE_DB, then demo/demo.duckdb)")
    p.add_argument("--out", default="", help="also write the message here")
    v = sub.add_parser("verify", help="re-measure a message on the producer's build")
    v.add_argument("--build", required=True, help="the producer's build (a DuckDB file), opened read-only")
    v.add_argument("--message", required=True, help="a file holding the message (the FEEDBACK block, or a text that contains one)")
    v.add_argument("--key-field", default=None)
    v.add_argument("--key-kind", default=None)
    v.add_argument("--key-count", type=int, default=None)
    v.add_argument("--json", default="", help="write the report as JSON here")
    a = ap.parse_args(argv)
    if a.command == "prepare":
        with GoldWarehouse(path=a.db) as wh:
            try:
                prepared = prepare(wh, a.field, a.kind, a.claim, a.query, _version())
            except FeedbackRefused as exc:
                print(f"REFUSED: {exc.reason}. Remedy: {exc.remedy}")
                return 2
        text = render(prepared)
        sys.stdout.write(text)
        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
        return 0
    text = Path(a.message).read_text(encoding="utf-8")
    report = verify(Path(a.build), text, a.key_field, a.key_kind, a.key_count)
    print_report(report)
    if a.json:
        Path(a.json).write_text(report_json(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
