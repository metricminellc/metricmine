"""CLI for the governed meaning commands (D-44).

`find`, `show`, `propose`, and `verify` are deterministic code, never
agents (D-10 Amendment G, CLAUDE.md rule 15): no model call, no network,
no loop, no MCP tool. This is a CLI, not the stdio server: stdout carries
results and stderr diagnostics.

The two commands that read a calendar, `propose` and `verify`, take the
day as a parameter (`--today`), so a test fixes it and no result turns
red on a date; without it the UTC day is used, the same day the scan
derives its states for. `find` and `show` read no calendar.

Exit codes: 0 done; 1 `verify` found what blocks a merge; 2 a refusal
or a usage error (nothing written).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from metricmine.documents.commands import parse_date as _date
from metricmine.documents.commands import today_or_utc as _today
from metricmine.documents.commands import tree_digest
from metricmine.documents.register import RegisterError
from metricmine.meaning import commands
from metricmine.meaning.register import load_all


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m metricmine.meaning",
        description=(
            "Governed meaning (D-44): find a term or a concept, show one with its"
            " bindings, run a change set into the outbox, and verify the registers."
            " Deterministic code, never an agent; it never writes under meaning/ or"
            " contracts/."
        ),
    )
    parser.add_argument("--repo", type=Path, default=None, help="the repository root (default: this checkout)")
    sub = parser.add_subparsers(dest="command", required=True)

    find = sub.add_parser("find", help="list terms and concepts by text, each with what carries it")
    find.add_argument("query", nargs="?", default="", help="a case-insensitive fragment of an id, a label, a definition, a synonym, or a parent id")

    show = sub.add_parser("show", help="print one term or concept with its bindings and their states")
    show.add_argument("id", help="a term_id or a concept_id")

    propose = sub.add_parser("propose", help="run a change set and render the registers as they would read into proposals/meaning/")
    propose.add_argument("file", type=Path, help="the change-set YAML file (by, intent, changes)")
    propose.add_argument("--today", type=_date, default=None, help="YYYY-MM-DD (default: today's UTC date)")
    propose.add_argument("--outbox", type=Path, default=None, help="where under proposals/meaning/ to render (default: proposals/meaning/<file stem>); a path outside it is refused")

    verify = sub.add_parser("verify", help="hold both registers to their contracts and derive every binding's state")
    verify.add_argument("--today", type=_date, default=None, help="YYYY-MM-DD (default: today's UTC date)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo = (args.repo or Path(__file__).resolve().parents[3]).resolve()
    try:
        if args.command == "verify":
            today = _today(args.today)
            result = commands.verify(repo, today)
            print(commands.render_verify(result, today), end="")
            return result.exit_code
        registers = load_all(repo)
        if args.command == "find":
            print(commands.render_find(commands.find(registers, args.query), args.query), end="")
            return 0
        if args.command == "show":
            print(commands.show(repo, registers, args.id), end="")
            return 0
        today = _today(args.today)
        before = (tree_digest(repo / "meaning"), tree_digest(repo / "contracts"))
        proposal, change_set, out = commands.propose(repo, registers, args.file, today, args.outbox)
        print((out / "summary.md").read_text(encoding="utf-8"), end="")
        try:
            where = out.relative_to(repo).as_posix()
        except ValueError:
            where = out.as_posix()
        if (tree_digest(repo / "meaning"), tree_digest(repo / "contracts")) != before:
            print(f"wrote {where}/; STOP: meaning/ or contracts/ changed during the write; restore them from git", file=sys.stderr)
            return 1
        print(f"wrote {where}/ (glossary/, ontology/, record.json, summary.md); meaning/ and contracts/ are unchanged")
        return 0
    except (commands.CommandError, RegisterError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
