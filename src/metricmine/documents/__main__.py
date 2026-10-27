"""CLI for the governed documents commands (D-43).

`find`, `inspect`, `bind`, and `verify` are deterministic code, never
agents (D-10 Amendment G, CLAUDE.md rule 15): no model call, no network,
no loop. This is a CLI, not the stdio server: stdout carries results and
stderr diagnostics (rule 18's stdout discipline governs
src/metricmine/server/ only).

The two commands that read a calendar, `bind` and `verify`, take the day
as a parameter (`--today`), so a test fixes it and no result turns red on
a date; without it the UTC day is used, the same day the scan derives its
states for. `find` and `inspect` read no calendar. A rooted path
(`${MM_DOCS_ROOT}/...`) resolves only when MM_DOCS_ROOT is mapped; CI and
the demo never map it.

Exit codes: 0 done; 1 `verify` found a failure; 2 a refusal or a usage
error (nothing written).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from metricmine.documents import commands
from metricmine.documents.commands import parse_date as _date
from metricmine.documents.commands import today_or_utc as _today
from metricmine.documents.register import RegisterError
from metricmine.documents.states import mapped_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m metricmine.documents",
        description=(
            "Governed documents (D-43): find a document, inspect its text, draft a"
            " binding into the outbox, and verify the register. Deterministic code,"
            " never an agent; it opens a document only in the repository or under"
            " MM_DOCS_ROOT, and it never writes the register."
        ),
    )
    parser.add_argument("--repo", type=Path, default=None, help="the repository root (default: this checkout)")
    sub = parser.add_subparsers(dest="command", required=True)

    find = sub.add_parser("find", help="list candidate documents by file name, with locations and text digests")
    find.add_argument("query", nargs="?", default="", help="a case-insensitive fragment of the file name")
    find.add_argument("--text", default=None, help="keep only documents whose extracted text contains this")

    inspect = sub.add_parser("inspect", help="print a document's parts, digest, and the sentences that match --grep")
    inspect.add_argument("document", help="a repository path, a ${MM_DOCS_ROOT}/ path, or a registered document id")
    inspect.add_argument("--grep", default=None, help="print the sentences containing this word, with locators")
    inspect.add_argument("--format", default=None, choices=list(commands.FORMATS), help="override the format the suffix implies")
    inspect.add_argument("--limit", type=int, default=20, help="how many matching sentences to print (default 20)")
    inspect.add_argument("--context", type=int, default=0, help="print this many neighboring sentences around each match")

    bind = sub.add_parser("bind", help="draft a binding into proposals/documents/; the register itself never changes here")
    bind.add_argument("document", help="a repository path, a ${MM_DOCS_ROOT}/ path, or a registered document id")
    bind.add_argument("--contract", required=True, help="the committed contract id")
    bind.add_argument("--column", required=True, help="the column of that contract")
    bind.add_argument("--anchor", required=True, help="the verbatim quote, taken from `inspect --grep`")
    bind.add_argument("--intent", required=True, help="the person's own words for this binding, recorded verbatim and hashed")
    bind.add_argument("--by", required=True, help="the person binding; an agent or model name is refused")
    bind.add_argument("--today", type=_date, default=None, help="YYYY-MM-DD (default: today's UTC date)")
    bind.add_argument("--document-id", default=None, help="the id for a new standing row (default: a slug of the title)")
    bind.add_argument("--title", default=None, help="the title, required for a document the register does not carry")
    bind.add_argument("--format", default=None, choices=list(commands.FORMATS), help="override the format the suffix implies")
    bind.add_argument("--review-by", type=_date, default=None, help="YYYY-MM-DD; default one year out in the repository, six months under MM_DOCS_ROOT")
    bind.add_argument("--governance", default=None, choices=["in_repo", "platform_governed", "pinned"])
    bind.add_argument("--certification-source", default=None, choices=["git_merge", "platform_approval", "steward_attestation", "none"])
    bind.add_argument("--gate-strength", default=None, choices=["publication_gate", "attestation_badge", "none"])
    bind.add_argument("--durable-id", default=None)
    bind.add_argument("--upstream-url", default=None, help="for a committed copy of a public document, its commit-pinned URL")
    bind.add_argument("--upstream-sha256", default=None, help="for a committed copy, the sha256 of the upstream bytes")
    bind.add_argument("--license", default=None, help="the document's license, as its publisher states it")
    bind.add_argument("--outbox", type=Path, default=None, help="where under proposals/ to write the draft (default: proposals/documents/<today>_<id>_<contract>.<column>); a path outside proposals/ is refused")

    verify = sub.add_parser("verify", help="hold the register to its contract and derive every document's state")
    verify.add_argument("--today", type=_date, default=None, help="YYYY-MM-DD (default: today's UTC date)")
    verify.add_argument("--reading-copy", action="append", default=[], metavar="ID=PATH",
                        help="verify a document's anchors against a staged copy (repeatable)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo = (args.repo or Path(__file__).resolve().parents[3]).resolve()
    root = mapped_root()
    try:
        if args.command == "verify":
            today = _today(args.today)
            copies = commands.parse_reading_copies(repo, args.reading_copy)
            result = commands.verify(repo, today, root, copies)
            print(commands.render_verify(result, today, root), end="")
            return result.exit_code
        register = commands.load_register_or_empty(repo)
        if args.command == "find":
            candidates = commands.find(repo, register, args.query, root, args.text)
            print(commands.render_find(candidates, args.query, root), end="")
            return 0
        target = commands.resolve_target(repo, register, args.document, root, args.format)
        if args.command == "inspect":
            extraction = commands._extract(target)
            print(commands.render_inspect(target, extraction, args.grep, args.limit, args.context), end="")
            return 0
        today = _today(args.today)
        draft = commands.bind(
            repo, register, target, args.contract, args.column, args.anchor, args.intent, args.by, today,
            document_id=args.document_id, title=args.title, review_by=args.review_by,
            governance=args.governance, certification_source=args.certification_source,
            gate_strength=args.gate_strength, upstream_url=args.upstream_url,
            upstream_sha256=args.upstream_sha256, license=args.license, durable_id=args.durable_id,
        )
        before = commands.tree_digest(repo / commands.REGISTER_DIR)
        out = commands.write_draft(repo, draft, args.outbox)
        print(commands.render_draft(repo, draft, out), end="")
        try:
            where = out.relative_to(repo).as_posix()
        except ValueError:
            where = out.as_posix()
        if commands.tree_digest(repo / commands.REGISTER_DIR) != before:
            print(f"wrote {where}/; STOP: {commands.REGISTER_DIR.as_posix()}/ changed during the write; restore it from git", file=sys.stderr)
            return 1
        print(f"wrote {where}/ (standing.yaml, bindings.yaml, DRAFT.md); the register is unchanged")
        return 0
    except (commands.CommandError, RegisterError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
