"""The scorer (E1T): the scores and the verdict by the key's rule, from the
ledger alone. Deterministic: the same inputs print the same lines.

    uv run python e1t/score.py --host claude-code|claude-desktop --build <producer warehouse.duckdb> [--out <dir>]

Reads each conversation folder under e1t/ledger/<host>/ (meta.json,
visible.md, capture.jsonl, message.txt), re-measures every accepted
prepare_feedback message on the producer's build with
`metricmine.feedback.verify`, and prints the scores and the verdict
lines exactly as the rule decides them. It reads no free text for
meaning: a call is matched by its arguments against the key, a message
verifies by the command's report, and fidelity is an exact comparison
of the message's five labeled lines against the visible reply after
whitespace folding. Writes scores.json, scores.md, and one verify.json
per conversation under --out (default e1t/ledger/<host>/scores/).

Scores over the fixture conversations (n per host):
  T1: an accepted prepare_feedback call with a field and kind the key accepts, in the first turn.
  T:  the same by the end of the conversation (after the fixed second turn when it was sent).
  V:  the last accepted acceptable call's message reproduces at the same contract versions on the producer's build.
  F:  the visible reply carries that message's five labeled lines verbatim.
  R:  refused prepare_feedback calls before that call (repairs), reported.
  C:  any accepted prepare_feedback call at all, whatever its field and kind, reported.
  K:  the message's count equals the key's count, reported and never required.
Controls and the canary are observed and reported, never scored. The
producer's build must carry the key's registry digest (content equal to
the served asset) and must not be the served file itself; otherwise the
scorer refuses, because a build that drifted would read as a tool-side
failure. The verdict lines are withheld while a host's batch is
incomplete.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import key  # noqa: E402
from driver import capture_calls, pf_calls, sha256_path  # noqa: E402
from metricmine.feedback import verify  # noqa: E402
from metricmine.feedback.layout import LABELS, extract_block, fold  # noqa: E402
from metricmine.feedback.prepare import registry_digest  # noqa: E402
from metricmine.query import GoldWarehouse  # noqa: E402

OFFER_WORDS = re.compile(r"\b(feedback|report (this|it)|owners?|prepare_feedback)\b", re.I)


def load(folder: Path) -> dict:
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    entries = []
    cap = folder / "capture.jsonl"
    if cap.is_file():
        for raw in cap.read_text(encoding="utf-8").splitlines():
            try:
                entries.append(json.loads(raw))
            except ValueError:
                continue
    _, calls = capture_calls(entries)
    pfs = pf_calls(calls)
    visible = (folder / "visible.md").read_text(encoding="utf-8") if (folder / "visible.md").is_file() else ""
    message = (folder / "message.txt").read_text(encoding="utf-8") if (folder / "message.txt").is_file() else ""
    return {"meta": meta, "calls": calls, "pfs": pfs, "visible": visible, "message": message}


def first_turn_pfs(conv: dict) -> list[dict]:
    """The prepare_feedback calls of the first turn: all of them when no
    second turn was sent; otherwise none (the second turn is sent only
    when the first turn made no call)."""
    return [] if conv["meta"].get("second_turn_sent") else conv["pfs"]


def accepted_call(pfs: list[dict], fixture: key.Fixture) -> dict | None:
    hits = [p for p in pfs if p.get("prepared") is True and p.get("message") and key.acceptable(fixture, str(p.get("field")), str(p.get("kind")))]
    return hits[-1] if hits else None


def fidelity(message: str, visible: str) -> tuple[bool, int]:
    block = extract_block(message)
    if block is None:
        return False, 0
    labeled = [ln for ln in block.splitlines() if ln.split(":", 1)[0].strip().lower() in LABELS]
    folded = fold(visible)
    present = sum(1 for ln in labeled if fold(ln) in folded)
    return present == len(labeled) == len(LABELS), present


class BuildMismatch(Exception):
    pass


def check_build(build: Path, expected_registry_md5: str = key.SERVED_REGISTRY_MD5, served_sha256: str = key.SERVED_SHA256) -> dict:
    """The producer's build is content equal to the served asset (the
    key's registry digest) and is not the served file itself."""
    with GoldWarehouse(path=build, scope="gold") as wh:
        rows, md5 = registry_digest(wh._con)
    sha = sha256_path(build)
    if md5 != expected_registry_md5:
        raise BuildMismatch(f"BUILD-MISMATCH the build's registry md5 {md5} is not the key's {expected_registry_md5}; a drifted build would read as a tool-side failure")
    if sha == served_sha256:
        raise BuildMismatch("BUILD-MISMATCH the build is the served file itself; the producer's build must be a different file")
    return {"registry_rows": rows, "registry_md5": md5, "sha256": sha}


def score_host(host: str, build: Path, out: Path, expected_registry_md5: str = key.SERVED_REGISTRY_MD5, served_sha256: str = key.SERVED_SHA256) -> dict:
    root = HERE / "ledger" / host
    out.mkdir(parents=True, exist_ok=True)
    build_check = check_build(build, expected_registry_md5, served_sha256)
    per: dict[str, dict] = {}
    controls: dict[str, dict] = {}
    canary: dict[str, dict] = {}
    attempts = sorted(p.name for p in root.iterdir() if p.is_dir() and ".attempt" in p.name)
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and (p / "meta.json").is_file() and ".attempt" not in p.name):
        conv = load(folder)
        fid = conv["meta"].get("fixture")
        if fid in key.BY_ID:
            fixture = key.BY_ID[fid]
            acc = accepted_call(conv["pfs"], fixture)
            acc1 = accepted_call(first_turn_pfs(conv), fixture)
            report = None
            if acc is not None:
                report = verify(build, acc["message"], acc["field"], acc["kind"], fixture.key_count)
                (out / f"{folder.name}.verify.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            fid_ok, present = fidelity(acc["message"], conv["visible"]) if acc else (False, 0)
            refused_before = 0
            if acc is not None:
                for p in conv["pfs"]:
                    if p is acc:
                        break
                    if p.get("prepared") is False:
                        refused_before += 1
            any_accepted = [p for p in conv["pfs"] if p.get("prepared") is True and p.get("message")]
            outside = [(p.get("field"), p.get("kind")) for p in any_accepted if not key.acceptable(fixture, str(p.get("field")), str(p.get("kind")))]
            per[folder.name] = {
                "fixture": fid, "repeat": conv["meta"].get("repeat"),
                "C": bool(any_accepted), "accepted_outside_key": outside,
                "K": bool(report and report.get("count_equals_key")),
                "volatile_calls": (report or {}).get("volatile_calls") or [],
                "T1": acc1 is not None, "T": acc is not None,
                "field": acc["field"] if acc else None, "kind": acc["kind"] if acc else None,
                "rows_matching": acc["rows_matching"] if acc else None,
                "V": bool(report and report.get("verifies")), "outcome": (report or {}).get("outcome"),
                "count_equals_key": (report or {}).get("count_equals_key"),
                "F": fid_ok, "labeled_lines_present": present, "R": refused_before,
                "prepare_feedback_calls": len(conv["pfs"]), "tool_calls": len(conv["calls"]),
                "second_turn_sent": bool(conv["meta"].get("second_turn_sent")),
                "seconds": conv["meta"].get("seconds"), "minutes": conv["meta"].get("minutes"),
                "cost_usd": conv["meta"].get("cost_usd"), "re_run_of": conv["meta"].get("re_run_of"),
            }
        elif fid in key.CONTROLS:
            controls[folder.name] = {
                "control": fid, "prepare_feedback_calls": len(conv["pfs"]), "tool_calls": len(conv["calls"]),
                "offer_words_in_reply": len(OFFER_WORDS.findall(conv["visible"])),
            }
        elif fid in key.CANARY_PROMPTS:
            text = fold(conv["visible"]).lower()
            if key.CANARY_PHRASE in text:
                reading = "pass"
            elif any(p in text for p in key.NO_INSTRUCTIONS_PHRASES):
                reading = "fail"
            else:
                reading = "ambiguous"
            canary[folder.name] = {"prompt": fid, "reading": reading, "tool_calls": len(conv["calls"])}
    repeats = key.CLAUDE_CODE_REPEATS if host == "claude-code" else key.DESKTOP_REPEATS
    n_expected = len(key.FIXTURES) * repeats
    n = len(per)
    t1 = sum(1 for p in per.values() if p["T1"])
    t = sum(1 for p in per.values() if p["T"])
    v = sum(1 for p in per.values() if p["V"])
    f = sum(1 for p in per.values() if p["F"])
    c = sum(1 for p in per.values() if p["C"])
    k = sum(1 for p in per.values() if p["K"])
    caller_side = sum(1 for p in per.values() if p["T"] and not p["V"] and p["volatile_calls"])
    complete = all(sum(1 for p in per.values() if p["fixture"] == fx.id) == repeats for fx in key.FIXTURES)
    if t == n and n > 0:
        called = "called every time"
    elif t >= n - key.RELIABLY_CALLED_MISSES and n > 0:
        called = "reliably called (one miss)"
    else:
        called = "not reliably called"
    if t == 0:
        verifies = "no accepted message to verify"
    elif v == t:
        verifies = "every tool message verified on the producer's build"
    elif v + caller_side == t:
        verifies = f"every tool message verified except {caller_side} with a volatile query (the caller's, reported)"
    else:
        verifies = "TOOL-SIDE-FAILURE: a message the tool produced did not verify; the tool is parked with its finding"
    fidelity_line = "rendered verbatim by the host" if (f == t and t > 0) else "not rendered verbatim in every reply (reported)"
    if not complete:
        called = verifies = fidelity_line = f"VERDICT-WITHHELD (incomplete: {n} of {n_expected} fixture conversations)"
    by_fixture = {}
    for fx in key.FIXTURES:
        rows = [p for p in per.values() if p["fixture"] == fx.id]
        by_fixture[fx.id] = {"n": len(rows), "T1": sum(p["T1"] for p in rows), "T": sum(p["T"] for p in rows), "V": sum(p["V"] for p in rows), "F": sum(p["F"] for p in rows), "R": sum(p["R"] for p in rows), "C": sum(p["C"] for p in rows), "K": sum(p["K"] for p in rows)}
    return {
        "host": host, "build": Path(build).name, "build_check": build_check, "complete": complete, "n": n, "n_expected": n_expected,
        "T1": t1, "T": t, "V": v, "F": f, "R": sum(p["R"] for p in per.values()), "C": c, "K": k,
        "verdict": {"called": called, "verifies": verifies, "fidelity": fidelity_line},
        "by_fixture": by_fixture, "per_conversation": per, "controls": controls, "canary": canary,
        "re_runs": {cid: p["re_run_of"] for cid, p in per.items() if p["re_run_of"]},
        "kept_attempts": attempts,
    }


def rel(path: Path) -> str:
    """A path as the worktree prints it, the same on every machine."""
    try:
        return path.resolve().relative_to(HERE.parent.resolve()).as_posix()
    except ValueError:
        return str(path)


def render(s: dict) -> str:
    lines = [f"# E1T scores: {s['host']}", ""]
    lines.append(f"build: registry md5 {s['build_check']['registry_md5']} ({s['build_check']['registry_rows']} rows), sha256 {s['build_check']['sha256'][:16]}")
    lines.append(f"complete: {s['complete']} ({s['n']} of {s['n_expected']} fixture conversations)")
    lines.append(f"T1 {s['T1']} of {s['n']} | T {s['T']} of {s['n']} | V {s['V']} of {s['T']} | F {s['F']} of {s['T']} | R {s['R']} | C {s['C']} of {s['n']} | K {s['K']} of {s['T']}")
    lines.append("")
    lines.append(f"CALLED {s['T']} of {s['n']}: {s['verdict']['called']}")
    lines.append(f"VERIFIES {s['V']} of {s['T']}: {s['verdict']['verifies']}")
    lines.append(f"FIDELITY {s['F']} of {s['T']}: {s['verdict']['fidelity']}")
    lines.append(f"REPORTED any accepted call C {s['C']} of {s['n']}; count equals the key K {s['K']} of {s['T']} (never a condition)")
    lines.append("")
    lines.append("| fixture | n | T1 | T | V | F | R | C | K |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for fid, b in s["by_fixture"].items():
        lines.append(f"| {fid} | {b['n']} | {b['T1']} | {b['T']} | {b['V']} | {b['F']} | {b['R']} | {b['C']} | {b['K']} |")
    lines.append("")
    lines.append("| id | fixture | T1 | T | C | field | kind | rows | V | outcome | K | F | lines | R | calls | 2nd turn | seconds | cost |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cid, p in s["per_conversation"].items():
        lines.append(
            f"| {cid} | {p['fixture']} | {p['T1']} | {p['T']} | {p['C']} | {p['field']} | {p['kind']} | {p['rows_matching']} | {p['V']} | {p['outcome']} | "
            f"{p['K']} | {p['F']} | {p['labeled_lines_present']} | {p['R']} | {p['tool_calls']} | {p['second_turn_sent']} | "
            f"{p['seconds'] if p['seconds'] is not None else p['minutes']} | {p['cost_usd']} |"
        )
    outside = {cid: p["accepted_outside_key"] for cid, p in s["per_conversation"].items() if p["accepted_outside_key"]}
    if outside:
        lines.append("")
        lines.append(f"Accepted calls outside the key's field and kind: {outside}")
    if s["controls"]:
        lines.append("")
        lines.append("Controls, observed and never scored (prepare_feedback calls / tool calls / offer words in the reply):")
        for cid, c in s["controls"].items():
            lines.append(f"- {cid} ({c['control']}): {c['prepare_feedback_calls']} / {c['tool_calls']} / {c['offer_words_in_reply']}")
    if s["canary"]:
        lines.append("")
        lines.append("Canary (the October 21 reading rule):")
        for cid, c in s["canary"].items():
            lines.append(f"- {cid} ({c['prompt']}): {c['reading']} (tool calls {c['tool_calls']})")
    lines.append("")
    lines.append(f"Re-runs reported: {s['re_runs'] or 'none'}; first attempts kept: {s['kept_attempts'] or 'none'}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", required=True, choices=["claude-code", "claude-desktop"])
    ap.add_argument("--build", required=True, help="the producer's build (a DuckDB file), opened read-only")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    out = Path(a.out) if a.out else HERE / "ledger" / a.host / "scores"
    try:
        s = score_host(a.host, Path(a.build), out)
    except BuildMismatch as exc:
        print(str(exc))
        return 2
    text = render(s)
    (out / "scores.json").write_text(json.dumps(s, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (out / "scores.md").write_text(text, encoding="utf-8")
    print(text, end="")
    print(f"SCORES-WRITTEN {rel(out / 'scores.json')} {rel(out / 'scores.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
