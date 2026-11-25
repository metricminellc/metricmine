"""The driven host (E1T): Claude Code in print mode, one fresh conversation
per key fixture and repeat, unattended between a batch's first line and
its evidence commit, with the stops in code.

    uv run python e1t/driver.py smoke    --model <alias-or-id> [--served <file>] [--worktree <dir>]
    uv run python e1t/driver.py fixtures --model <alias-or-id> [--repeats 5]
    uv run python e1t/driver.py controls --model <alias-or-id> [--repeats 3]
    uv run python e1t/driver.py canary   --model <alias-or-id>
    uv run python e1t/driver.py status

Each conversation runs `claude -p` from a fresh temporary directory
outside any git worktree, so no CLAUDE.md of a project reaches the host,
with the branch's server as the only MCP server (--mcp-config and
--strict-mcp-config), the built-in tools off (--tools ""), the six server
tools pre-approved, --permission-mode dontAsk, no settings files
(--setting-sources ""), the model named, a turn cap, and a dollar cap per
call; the server runs through the capture shim, so every JSON-RPC message
of the conversation lands in the conversation's own capture files (one
per server process; a second turn through --resume starts a second
process). The ledger (e1t/ledger/claude-code/) holds, per conversation,
the prompt, the host's stream (stream.jsonl), the final visible text
(visible.md), the merged capture (capture.jsonl), the host's result
records (result.json), the last accepted prepare_feedback message
(message.txt), and meta.json; one line per conversation goes to
ledger.jsonl. Paths of this machine are replaced by placeholders before
anything is written, and the screen runs before any commit.

Stops in code: the served file is not the key's; the smoke's capture
does not carry the key's instructions digest and six tools; a
conversation whose capture carries no initialize (the server did not
start); the host's model or version changing inside a batch; the batch's
reported-cost bound; the host exiting without a result record and
without a first answer (a technical failure of the key's list, re-run
once with the first attempt kept as <id>.attempt1, then a stop). A
conversation that gave a first answer is never re-run. The fixed second
turn is sent only by the key's rule. No proposer is called and no API
key is in the environment: the host authenticates as the person is
signed in.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import key  # noqa: E402

HOST = "claude-code"
LEDGER = HERE / "ledger" / HOST
SERVER_TOOLS = ("list_fact_categories", "get_schema", "get_context", "query", "lookup_record", "prepare_feedback")
PF_TOOL = f"mcp__{key.SERVER_NAME}__{key.TOOL_NAME}"
INIT_KEYS = ("model", "claude_code_version", "permissionMode", "tools", "mcp_servers", "apiKeySource", "memory_paths", "skills", "agents", "plugins", "cwd")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def claude_version() -> str:
    try:
        return subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def conditions(worktree: Path) -> dict:
    """What else shaped the host on this machine, recorded as digests, never content."""
    home = Path.home()
    out = {"claude_code_version": claude_version()}
    for name, path in (("user_settings", home / ".claude" / "settings.json"), ("user_claude_md", home / ".claude" / "CLAUDE.md")):
        out[name] = sha256_path(path)[:16] if path.is_file() else "absent"
    out["worktree_head"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=worktree, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain", "--", ".", ":!e1t/ledger"], cwd=worktree, capture_output=True, text=True).stdout
    # (not stripped: a porcelain line's first character may be a space)
    # The top-level names of whatever is dirty outside the ledger (a prep's
    # staging folder, say), never their contents: the record says what else
    # sat in the worktree.
    names = sorted({ln[3:].split("/", 1)[0] + ("/" if "/" in ln[3:] else "") for ln in status.splitlines() if len(ln) > 3})
    out["worktree_dirty_outside_ledger"] = names
    return out


class Scrubber:
    def __init__(self, worktree: Path, served: Path) -> None:
        tmp = tempfile.gettempdir()
        raw = [str(worktree.resolve()), str(worktree), str(served.resolve()), str(LEDGER.resolve()), os.path.realpath(tmp), tmp, str(Path.home())]
        pairs: list[tuple[str, str]] = []
        for value, placeholder in zip(raw, ("<worktree>", "<worktree>", "<served>", "<ledger>", "<tmp>", "<tmp>", "<home>")):
            if value and value != "/":
                pairs.append((value, placeholder))
                # Claude Code names a project folder by its path with separators as dashes.
                pairs.append((value.replace("/", "-"), placeholder))
        self.pairs = sorted(set(pairs), key=lambda p: -len(p[0]))

    def __call__(self, text: str) -> str:
        for raw, placeholder in self.pairs:
            text = text.replace(raw, placeholder)
        return text


def plan(batch: str, repeats: int) -> list[tuple[str, str, str, int]]:
    """(cid, fixture or control id, prompt, repeat)"""
    if batch == "smoke":
        return [("cc-smoke", "SMOKE", key.SMOKE, 0)]
    if batch == "fixtures":
        return [(f"cc-{f.id}-r{r}", f.id, f.prompt, r) for r in range(1, repeats + 1) for f in key.FIXTURES]
    if batch == "controls":
        return [(f"cc-{p}-r{r}", p, text, r) for r in range(1, repeats + 1) for p, text in key.CONTROLS.items()]
    if batch == "canary":
        return [(f"cc-{c}", c, text, 0) for c, text in key.CANARY_PROMPTS.items()]
    raise SystemExit(f"DRIVER-STOP unknown batch {batch!r}")


def command(prompt: str, mcp_config: Path, model: str, resume: str | None) -> list[str]:
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--mcp-config", str(mcp_config), "--strict-mcp-config",
        "--tools", "",
        "--allowedTools", *[f"mcp__{key.SERVER_NAME}__{t}" for t in SERVER_TOOLS],
        "--permission-mode", "dontAsk",
        "--model", model,
        "--max-turns", str(key.MAX_TURNS),
        "--max-budget-usd", str(key.PER_TURN_BUDGET_USD),
        "--setting-sources", "",
    ]
    if resume:
        cmd += ["--resume", resume]
    return cmd


def run_turn(prompt: str, cwd: Path, mcp_config: Path, model: str, resume: str | None, env: dict) -> tuple[list[dict], str, int, float]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command(prompt, mcp_config, model, resume),
            cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=key.PER_TURN_TIMEOUT_S,
        )
        out, err, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = (exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")) + "\nDRIVER: timeout"
        code = -1
    seconds = round(time.monotonic() - started, 2)
    events: list[dict] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except ValueError:
            events.append({"type": "raw", "line": line})
    return events, err, code, seconds


def result_of(events: list[dict]) -> dict | None:
    for e in reversed(events):
        if e.get("type") == "result":
            return e
    return None


def init_of(events: list[dict]) -> dict | None:
    for e in events:
        if e.get("type") == "system" and e.get("subtype") == "init":
            return e
    return None


def visible_text(events: list[dict]) -> str:
    """The assistant's text blocks of this turn, in order; the result's own
    text when the stream carried no assistant text."""
    parts: list[str] = []
    for e in events:
        if e.get("type") != "assistant":
            continue
        for block in (e.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                parts.append(block["text"])
    if parts:
        return "\n\n".join(parts).strip()
    r = result_of(events)
    return str((r or {}).get("result") or "").strip()


def host_tool_uses(events: list[dict]) -> list[dict]:
    uses = []
    for e in events:
        if e.get("type") != "assistant":
            continue
        for block in (e.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                uses.append({"name": block.get("name"), "input": block.get("input")})
    return uses


def read_capture(capture_dir: Path) -> list[dict]:
    entries: list[dict] = []
    for path in sorted(capture_dir.glob("capture-*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            try:
                entries.append(json.loads(raw))
            except ValueError:
                continue
    return entries


def wait_for_exit_lines(capture_dir: Path, expected: int, timeout_s: float = 10.0) -> bool:
    """The shim writes `server exited` as its last line; wait for one per
    server process so the capture never trails the host."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        exits = sum(1 for e in read_capture(capture_dir) if e.get("dir") == "shim" and str(e.get("line", "")).startswith("server exited"))
        if exits >= expected:
            return True
        time.sleep(0.2)
    return False


def capture_calls(entries: list[dict]) -> tuple[bool, list[dict]]:
    """(an initialize was answered, the tools/call pairs in order: name,
    arguments, result dict or error)"""
    initialized = False
    pending: dict = {}
    calls: list[dict] = []
    for e in entries:
        try:
            msg = json.loads(e.get("line", ""))
        except ValueError:
            continue
        if not isinstance(msg, dict):
            continue
        if e.get("dir") == "client":
            if msg.get("method") == "tools/call":
                params = msg.get("params") or {}
                pending[msg.get("id")] = {"t": e.get("t"), "name": params.get("name"), "arguments": params.get("arguments") or {}}
        elif e.get("dir") == "server":
            if "result" in msg and isinstance(msg["result"], dict) and "instructions" in msg["result"]:
                initialized = True
            if msg.get("id") in pending:
                call = pending.pop(msg["id"])
                res = msg.get("result") if "result" in msg else {"error": msg.get("error")}
                call["result"] = res
                calls.append(call)
    return initialized, calls


def capture_surface(entries: list[dict]) -> dict:
    """What the server told this host at the handshake: the instructions'
    length and sha256 and the tool names, read from the capture."""
    out: dict = {"instructions_sha256": None, "instructions_length": None, "tools": None}
    for e in entries:
        if e.get("dir") != "server":
            continue
        try:
            msg = json.loads(e.get("line", ""))
        except ValueError:
            continue
        res = msg.get("result") if isinstance(msg, dict) else None
        if isinstance(res, dict) and "instructions" in res and out["instructions_sha256"] is None:
            text = res.get("instructions") or ""
            out["instructions_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            out["instructions_length"] = len(text)
        if isinstance(res, dict) and isinstance(res.get("tools"), list) and out["tools"] is None:
            out["tools"] = [t.get("name") for t in res["tools"] if isinstance(t, dict)]
    return out


def surface_matches_key(surface: dict) -> bool:
    return (
        surface.get("instructions_sha256") == key.INSTRUCTIONS_SHA256
        and surface.get("instructions_length") == key.INSTRUCTIONS_LENGTH
        and surface.get("tools") is not None
        and len(surface["tools"]) == key.TOOL_COUNT
        and key.TOOL_NAME in surface["tools"]
    )


def pf_calls(calls: list[dict]) -> list[dict]:
    out = []
    for c in calls:
        if c.get("name") != key.TOOL_NAME:
            continue
        res = c.get("result") or {}
        sc = res.get("structuredContent") if isinstance(res, dict) else None
        if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
            sc = sc["result"]
        out.append({
            "t": c.get("t"),
            "field": (c.get("arguments") or {}).get("field"),
            "kind": (c.get("arguments") or {}).get("kind"),
            "prepared": (sc or {}).get("prepared"),
            "reason": (sc or {}).get("reason"),
            "message": (sc or {}).get("message"),
            "rows_matching": (sc or {}).get("rows_matching"),
        })
    return out


def accepted_pf_calls(calls: list[dict]) -> list[dict]:
    return [p for p in pf_calls(calls) if p.get("prepared") is True and p.get("message")]


def run_conversation(cid: str, fid: str, prompt: str, repeat: int, batch: str, model: str, worktree: Path, served: Path, scrub: Scrubber, re_run_of: str | None = None) -> dict:
    folder = LEDGER / cid
    if folder.exists() and (folder / "meta.json").is_file():
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        if meta.get("first_answer"):
            print(f"DRIVER-STOP {cid} already gave a first answer; a conversation that gave a first answer is never re-run")
            raise SystemExit(3)
        attempt = LEDGER / f"{cid}.attempt1"
        if attempt.exists():
            print(f"DRIVER-STOP {cid} was already re-run once ({attempt.name} exists)")
            raise SystemExit(3)
        folder.rename(attempt)
    folder.mkdir(parents=True)
    capture_dir = folder / "capture"
    capture_dir.mkdir()
    cwd = Path(tempfile.mkdtemp(prefix="e1t-"))  # outside any git worktree: no project CLAUDE.md reaches the host
    mcp_config = folder / "mcp.json"
    # Absolute paths with symlinks kept: the venv's `python` is a symlink
    # to the interpreter, and resolving it would name the system
    # interpreter with no venv (measured in Prep D's tests and again here).
    mcp_config.write_text(json.dumps({"mcpServers": {key.SERVER_NAME: {
        "command": os.path.abspath(worktree / ".venv" / "bin" / "python"),
        "args": [os.path.abspath(worktree / "e1t" / "capture_shim.py")],
        "env": {"MM_SERVE_DB": os.path.abspath(served), "MM_E1T_CAPTURE": os.path.abspath(capture_dir)},
    }}}, indent=1) + "\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("MM_") and k != "ANTHROPIC_API_KEY"}
    (folder / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    started = now()
    events, err, code, seconds = run_turn(prompt, cwd, mcp_config, model, None, env)
    turns = [{"turn": 1, "prompt": prompt, "events": events, "stderr": err, "exit": code, "seconds": seconds}]
    result = result_of(events)
    second_turn = None
    first_text = visible_text(events)
    asks = key.ends_with_question(first_text)
    wait_for_exit_lines(capture_dir, 1)
    entries_first = read_capture(capture_dir)
    _, calls_first = capture_calls(entries_first)
    first_turn_capture_lines = len(entries_first)
    if result is not None and fid in key.BY_ID and not accepted_pf_calls(calls_first) and asks:
        second_turn = key.SECOND_TURN
        events2, err2, code2, seconds2 = run_turn(second_turn, cwd, mcp_config, model, result.get("session_id"), env)
        turns.append({"turn": 2, "prompt": second_turn, "events": events2, "stderr": err2, "exit": code2, "seconds": seconds2})
        result = result_of(events2) or result
        wait_for_exit_lines(capture_dir, 2)
    ended = now()
    entries = read_capture(capture_dir)
    initialized, calls = capture_calls(entries)
    surface = capture_surface(entries)
    pfs = pf_calls(calls)
    accepted = accepted_pf_calls(calls)
    init = init_of(turns[0]["events"])
    all_events = [e for t in turns for e in t["events"]]
    visible = "\n\n".join(f"## user {t['turn']}\n{t['prompt']}\n\n## assistant {t['turn']}\n{visible_text(t['events'])}" for t in turns)
    costs = [float((result_of(t["events"]) or {}).get("total_cost_usd") or 0.0) for t in turns]
    meta = {
        "id": cid, "host": HOST, "batch": batch, "fixture": fid, "repeat": repeat, "model_requested": model,
        "model_reported": (init or {}).get("model"), "models_used": sorted(((result or {}).get("modelUsage") or {}).keys()),
        "init": {k: (init or {}).get(k) for k in INIT_KEYS},
        "started": started, "ended": ended, "seconds": round(sum(t["seconds"] for t in turns), 2), "seconds_per_turn": [t["seconds"] for t in turns],
        "cost_usd": round(sum(costs), 6), "cost_usd_per_turn": costs, "num_turns_reported": (result or {}).get("num_turns"),
        "result_subtype": (result or {}).get("subtype"), "is_error": (result or {}).get("is_error"),
        "exit_codes": [t["exit"] for t in turns], "first_answer": bool(first_text),
        "first_answer_ends_with_question": asks, "second_turn_sent": second_turn is not None,
        "first_turn_capture_lines": first_turn_capture_lines,
        "capture_initialized": initialized, "capture_surface": surface, "capture_surface_matches_key": surface_matches_key(surface),
        "capture_tool_calls": len(calls), "capture_tool_names": [c.get("name") for c in calls],
        "host_tool_uses": [u["name"] for u in host_tool_uses(all_events)],
        "prepare_feedback_calls": [{k: v for k, v in p.items() if k != "message"} for p in pfs],
        "prepare_feedback_accepted": len(accepted), "re_run_of": re_run_of,
    }
    (folder / "stream.jsonl").write_text(scrub("\n".join(json.dumps(e, ensure_ascii=False) for e in all_events) + "\n"), encoding="utf-8")
    (folder / "stderr.txt").write_text(scrub("\n".join(t["stderr"] for t in turns)), encoding="utf-8")
    (folder / "visible.md").write_text(scrub(visible) + "\n", encoding="utf-8")
    (folder / "result.json").write_text(scrub(json.dumps([result_of(t["events"]) for t in turns], indent=1, ensure_ascii=False)) + "\n", encoding="utf-8")
    (folder / "capture.jsonl").write_text(scrub("\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"), encoding="utf-8")
    (folder / "message.txt").write_text(accepted[-1]["message"] if accepted else "", encoding="utf-8")
    (folder / "meta.json").write_text(scrub(json.dumps(meta, indent=1, ensure_ascii=False)) + "\n", encoding="utf-8")
    shutil.rmtree(capture_dir, ignore_errors=True)
    shutil.rmtree(cwd, ignore_errors=True)
    mcp_config.unlink(missing_ok=True)
    return meta


LEDGER_KEYS = ("id", "batch", "fixture", "repeat", "model_reported", "started", "ended", "seconds", "cost_usd", "num_turns_reported",
               "result_subtype", "capture_initialized", "capture_surface_matches_key", "capture_tool_calls", "prepare_feedback_accepted",
               "second_turn_sent", "re_run_of")


def ledger_line(meta: dict) -> str:
    return json.dumps({k: meta.get(k) for k in LEDGER_KEYS}, ensure_ascii=False)


def ledger_rows(ledger: Path) -> list[dict]:
    rows = []
    if ledger.is_file():
        for raw in ledger.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(raw))
            except ValueError:
                pass
    return rows


def spent(ledger: Path, batch: str | None = None) -> float:
    return round(sum(float(r.get("cost_usd") or 0.0) for r in ledger_rows(ledger) if batch is None or r.get("batch") == batch), 6)


def cmd_batch(batch: str, model: str, repeats: int, worktree: Path, served: Path) -> int:
    LEDGER.mkdir(parents=True, exist_ok=True)
    ledger = LEDGER / "ledger.jsonl"
    cond = conditions(worktree)
    (LEDGER / "conditions.json").write_text(json.dumps(cond, indent=1) + "\n", encoding="utf-8")
    scrub = Scrubber(worktree, served)
    served_sha = sha256_path(served)
    print(
        f"BATCH {batch} host {HOST} {cond['claude_code_version']} model {model} worktree {cond['worktree_head']}"
        f"{' dirty-outside-ledger ' + ','.join(cond['worktree_dirty_outside_ledger']) if cond['worktree_dirty_outside_ledger'] else ''} served sha256 {served_sha[:16]} "
        f"spent-before {spent(ledger, batch):.4f}"
    )
    if served_sha != key.SERVED_SHA256:
        print("DRIVER-STOP the served file is not the key's (sha256 mismatch)")
        return 2
    if batch != "smoke" and not (LEDGER / "cc-smoke" / "meta.json").is_file():
        print("DRIVER-STOP the smoke conversation has not run; run `smoke` first")
        return 2
    held: dict | None = None  # the batch's first conversation's model and version
    for cid, fid, prompt, repeat in plan(batch, repeats):
        if spent(ledger, batch) > key.BATCH_BUDGET_USD:
            print(f"DRIVER-STOP the batch bound ({key.BATCH_BUDGET_USD} USD of reported cost) is reached before {cid}")
            return 2
        if (LEDGER / cid / "meta.json").is_file() and json.loads((LEDGER / cid / "meta.json").read_text(encoding="utf-8")).get("first_answer"):
            print(f"SKIP {cid} already in the ledger")
            continue
        meta = run_conversation(cid, fid, prompt, repeat, batch, model, worktree, served, scrub)
        if not meta["capture_initialized"]:
            with open(ledger, "a", encoding="utf-8") as fh:
                fh.write(ledger_line(meta) + "\n")
            print(f"DRIVER-STOP {cid}: {key.SERVER_DID_NOT_START}; nothing scored")
            return 2
        if not meta["capture_surface_matches_key"]:
            with open(ledger, "a", encoding="utf-8") as fh:
                fh.write(ledger_line(meta) + "\n")
            print(f"DRIVER-STOP {cid}: the server's surface is not the key's ({json.dumps(meta['capture_surface'])})")
            return 2
        if meta["result_subtype"] is None and not meta["first_answer"]:
            reason = key.TECHNICAL_FAILURES[0] if meta["exit_codes"][0] != 0 else key.TECHNICAL_FAILURES[1]
            print(f"RE-RUN {cid}: {reason}")
            meta = run_conversation(cid, fid, prompt, repeat, batch, model, worktree, served, scrub, re_run_of=reason)
            if meta["result_subtype"] is None and not meta["first_answer"]:
                with open(ledger, "a", encoding="utf-8") as fh:
                    fh.write(ledger_line(meta) + "\n")
                print(f"DRIVER-STOP {cid}: no result after one re-run")
                return 2
        with open(ledger, "a", encoding="utf-8") as fh:
            fh.write(ledger_line(meta) + "\n")
        print(
            f"CONVERSATION {cid} fixture {fid} model {meta['model_reported']} seconds {meta['seconds']} cost {meta['cost_usd']:.4f} "
            f"turns {meta['num_turns_reported']} tool-calls {meta['capture_tool_calls']} prepare_feedback {len(meta['prepare_feedback_calls'])} "
            f"accepted {meta['prepare_feedback_accepted']} second-turn {meta['second_turn_sent']} subtype {meta['result_subtype']}"
        )
        this = {"model_reported": meta["model_reported"], "claude_code_version": meta["init"].get("claude_code_version")}
        if held is None:
            held = this
        elif this != held:
            print(f"DRIVER-STOP {cid}: the host or the model changed inside the batch ({held} then {this})")
            return 2
        if batch == "smoke":
            ok = "list_fact_categories" in meta["capture_tool_names"]
            print("SMOKE-OK capture written, the surface is the key's, and list_fact_categories was called" if ok else "DRIVER-STOP the smoke conversation did not call list_fact_categories")
            return 0 if ok else 2
    print(f"BATCH-DONE {batch} spent {spent(ledger, batch):.4f} USD of {key.BATCH_BUDGET_USD} (reported cost)")
    return 0


def cmd_status() -> int:
    ledger = LEDGER / "ledger.jsonl"
    rows = ledger_rows(ledger)
    print(f"STATUS {len(rows)} conversations in the ledger, {spent(ledger):.4f} USD reported")
    for r in rows:
        print(f"  {r['id']} {r.get('batch')} {r['fixture']} r{r['repeat']} {r['seconds']}s {float(r['cost_usd'] or 0):.4f} accepted {r['prepare_feedback_accepted']} subtype {r['result_subtype']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("batch", choices=["smoke", "fixtures", "controls", "canary", "status"])
    ap.add_argument("--model", default="")
    ap.add_argument("--repeats", type=int, default=0)
    ap.add_argument("--worktree", default=str(HERE.parent))
    ap.add_argument("--served", default=str(HERE / "served" / f"demo-{key.SERVED_RELEASE}.duckdb"))
    a = ap.parse_args(argv)
    if a.batch == "status":
        return cmd_status()
    if not a.model:
        print("DRIVER-STOP --model is required and is recorded in the ledger")
        return 2
    repeats = a.repeats or (key.CLAUDE_CODE_CONTROL_REPEATS if a.batch == "controls" else key.CLAUDE_CODE_REPEATS)
    return cmd_batch(a.batch, a.model, repeats, Path(a.worktree), Path(a.served))


if __name__ == "__main__":
    sys.exit(main())
