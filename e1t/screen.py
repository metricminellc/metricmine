"""The screen (E1T): every file reaches the public branch through this.

    uv run python e1t/screen.py [--authored] <file-or-directory> ...

A ledger committed on a public branch is public. Before every commit
this command reads each file and BLOCKS it when a line carries a class
the key names: a local path, an account or machine name, an email
address, a token or key, or employer and career language (the copy
rule). It REPORTS, and never blocks, the classes the finding records:
em dashes (a model's own text is quoted as evidence) and document
references. With --authored (the key, the README, the record) an em dash
blocks too. The capture's query statements must name the gold schema
alone, which the served file and the scope gate already hold; the screen
checks it again.

The account and machine names are never written in this file: the
sitting derives them on the Mac (whoami, hostname -s, the account's full
name, and the employer's name typed once) into
e1t/local/screen_names.txt (gitignored), one
per line, and the screen reads that file when it exists. Without it the
screen prints SCREEN-NAMES-MISSING, blocks nothing by name, and ends with
SCREEN-BLOCKED ... names file missing, so a
commit step refuses on that line.

It prints the class and the line numbers of a block, never the matched
text, so the terminal log stays clean. The last line is SCREEN-CLEAN <n>
files or SCREEN-BLOCKED <n> files. Deterministic: no clock, no network.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES_FILE = HERE / "local" / "screen_names.txt"

BLOCK = {
    # A Windows path is a lone drive letter, a colon, one to four backslashes
    # (plain text, JSON, and a capture's JSON-in-JSON), then a path character
    # that is not a JSON escape: "scope:\\n the" in a captured description is
    # an encoded newline, never a drive.
    "local path": re.compile(r"(/Users/|/home/[a-z]|/private/|/Volumes/|(?<!\w)[A-Za-z]:\\{1,4}(?!n\b|t\b|r\b)[A-Za-z0-9_$.]|(?<![\w/])~/)"),
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "token or key": re.compile(
        r"(sk-ant-|\bsk-[A-Za-z0-9]{8,}|\bghp_|\bgho_|\bghu_|\bghs_|github_pat_|\bAKIA[0-9A-Z]{16}\b|\bxox[abp]-|Bearer\s+[A-Za-z0-9._-]{8,}|ANTHROPIC_API_KEY=)"
    ),
    "employer or career language": re.compile(
        r"\b(portfolio|hiring|job[ -]search|r[ée]sum[ée]|linkedin|career|interview|employer)\b", re.I
    ),
}
REPORT = {
    "em dash": re.compile("—"),
    "document reference": re.compile(r"(https?://|\bdocuments?\b|\bsources?\b|\blocator\b|\.Rd\b|nycflights13|\bregister\b)", re.I),
}
NON_GOLD = re.compile(r"\b(bronze|silver|main|information_schema|pg_catalog)\s*\.", re.I)


MIN_NAME = 4


def read_names(path: Path = NAMES_FILE) -> tuple[list[str], list[str]]:
    """(the names screened, the names too short to screen). A name is matched
    as a whole word, case-insensitively; a name under four characters (a
    hostname like `vm`, say) would match inside random strings and is set
    aside, and the screen says so."""
    if not path.is_file():
        return [], []
    names = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    return [n for n in names if len(n) >= MIN_NAME], [n for n in names if len(n) < MIN_NAME]


def load_names(path: Path = NAMES_FILE) -> re.Pattern | None:
    names, _ = read_names(path)
    if not names:
        return None
    return re.compile(r"(?<![\w-])(" + "|".join(re.escape(n) for n in names) + r")(?![\w-])", re.I)


def screen_file(path: Path, authored: bool, names: re.Pattern | None) -> tuple[dict[str, list[int]], dict[str, int]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks: dict[str, list[int]] = {}
    reports: dict[str, int] = {}
    classes = dict(BLOCK)
    if names is not None:
        classes["account or machine name"] = names
    if authored:
        classes["em dash"] = REPORT["em dash"]
    for n, line in enumerate(text.splitlines(), 1):
        for name, rx in classes.items():
            if rx.search(line):
                blocks.setdefault(name, []).append(n)
        for name, rx in REPORT.items():
            if name == "em dash" and authored:
                continue
            if rx.search(line):
                reports[name] = reports.get(name, 0) + 1
    if path.suffix == ".jsonl":
        for n, raw in enumerate(text.splitlines(), 1):
            try:
                entry = json.loads(raw)
                msg = json.loads(entry["line"]) if "line" in entry else entry
            except (ValueError, KeyError, TypeError):
                continue
            if isinstance(msg, dict) and msg.get("method") == "tools/call":
                args = (msg.get("params") or {}).get("arguments") or {}
                for key in ("sql", "query"):
                    sql = args.get(key) if isinstance(args, dict) else None
                    if isinstance(sql, str) and NON_GOLD.search(sql):
                        blocks.setdefault("query outside gold", []).append(n)
    return blocks, reports


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--authored", action="store_true", help="an authored file: em dashes block")
    ap.add_argument("--names", default=str(NAMES_FILE), help="the local names file (gitignored)")
    a = ap.parse_args(argv)
    names = load_names(Path(a.names))
    if names is None:
        print(f"SCREEN-NAMES-MISSING {a.names}: no account or machine name is screened; the commit step refuses on this line")
    else:
        kept, short = read_names(Path(a.names))
        print(f"SCREEN-NAMES {len(kept)} name(s) screened as whole words" + (f"; {len(short)} under {MIN_NAME} characters set aside" if short else ""))
    files: list[Path] = []
    for p in a.paths:
        path = Path(p)
        if path.is_dir():
            files.extend(sorted(q for q in path.rglob("*") if q.is_file()))
        else:
            files.append(path)
    blocked = 0
    for path in files:
        blocks, reports = screen_file(path, a.authored, names)
        rep = "; ".join(f"{k} {v}" for k, v in sorted(reports.items())) or "none"
        if blocks:
            blocked += 1
            detail = "; ".join(f"{k}: line(s) {', '.join(map(str, v[:10]))}" for k, v in sorted(blocks.items()))
            print(f"SCREEN {path}: BLOCKED {detail} | reported: {rep}")
        else:
            print(f"SCREEN {path}: OK | reported: {rep}")
    if names is None:
        # the summary line is the only line a commit step reads, so the missing
        # names file blocks there, not only in the first line
        print(f"SCREEN-BLOCKED {len(files)} files, names file missing" + (f", {blocked} blocked" if blocked else ""))
        return 1
    print(f"{'SCREEN-BLOCKED' if blocked else 'SCREEN-CLEAN'} {len(files)} files" + (f", {blocked} blocked" if blocked else ""))
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
