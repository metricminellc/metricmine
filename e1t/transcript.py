"""The scripted host (E1T): Claude Desktop, one fresh conversation per key
fixture and repeat, driven by a person at the keyboard under a fixed
protocol, with the capture shim as the record of the tool calls.

    uv run python e1t/transcript.py ids
    uv run python e1t/transcript.py new <id> --app-version <v> --model <m>
    uv run python e1t/transcript.py paste <id> [--from <file>]
    uv run python e1t/transcript.py turn <id>
    uv run python e1t/transcript.py finish <id> [--minutes <n>] [--re-run-of "<reason>"]
    uv run python e1t/transcript.py abandon <id> --reason "<reason>"

Why Desktop is scripted and not driven: the app exposes no command line
and no API that starts a conversation or sends a message, and its own
MCP log keeps methods, never payloads (measured October 21, 2026). So a
person sends the key's fixed words, pastes each reply whole with
Desktop's copy control, and the capture shim keeps the JSON-RPC record.

`new` marks the live shim's capture file (one Desktop session is one
server process, so the initialize sits before the mark: "the server
started" means the live file holds an initialize before the mark, and
the handshake's instructions digest and tool count are checked against
the key), refuses when a mark or an unfinished conversation exists,
creates e1t/ledger/claude-desktop/<id>/ with meta.json, prompt.txt, and
a visible.md whose user turn is the key's text and whose assistant
section is left for the paste, prints the SEND line, and puts the same
words on the clipboard (`pbcopy`) so the person pastes them into Desktop
rather than retyping them. `paste` writes the clipboard (`pbpaste`, or
`--from <file>`) into the first open assistant section, byte for byte,
so no editor touches the reply; it refuses an empty clipboard and a
clipboard that still holds the words `new` or `turn` put there. `turn` reads
the pasted first answer and the capture since the mark and applies the
key's rule: the fixed second turn is sent only when the first turn
produced no accepted prepare_feedback call and the first answer ended
with a question to the person; it prints TURN-SECOND with the text, or
TURN-NONE, and records the capture's line count at the turn boundary.
`finish` holds every section pasted, checks the live shim is still the
marked one, slices the capture into the folder, writes message.txt from
the last accepted prepare_feedback result in the capture, warns when
none of that message's labeled lines appears in the paste, records the
measures, and prints one TRANSCRIPT-OK line. `abandon` is the one re-run
door the key allows: a conversation with no pasted answer is kept as
<id>.attempt1 under one of the key's technical-failure reasons, the mark
is released, and `new` may start it once more; its `finish` then passes
--re-run-of with that reason. Under the key's host-error reason (the app
showed an error of its own before the model wrote anything or called a
tool), `abandon` keeps the conversation under host-errors/, spends no
re-run, and `new` starts it again. A conversation that gave a first answer is
never re-run, and a server Desktop restarted mid-conversation (the live
shim is not the marked one at `finish`) is a stop. Every printed line is
a measurement. No model, no network.

The ids and their order: cd-smoke, cd-C1, cd-C2 (the canary's two, one
turn each, observed and never scored), then per repeat r in 1..3:
cd-F1-r<r>, cd-F2-r<r>, cd-F3-r<r>.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import capture_slice  # noqa: E402
import key  # noqa: E402
from driver import accepted_pf_calls, capture_calls, capture_surface, pf_calls, surface_matches_key  # noqa: E402

HOST = "claude-desktop"
LEDGER = HERE / "ledger" / HOST
PLACEHOLDER = "<paste the assistant's reply here, whole, with Desktop's copy control on that message>"

IDS: list[tuple[str, str, int]] = [("cd-smoke", "SMOKE", 0)] + [(f"cd-{c}", c, 0) for c in key.CANARY_PROMPTS]
for _r in range(1, key.DESKTOP_REPEATS + 1):
    for _f in key.FIXTURES:
        IDS.append((f"cd-{_f.id}-r{_r}", _f.id, _r))
BY_ID = {i[0]: i for i in IDS}


def prompt_for(fid: str) -> str:
    if fid == "SMOKE":
        return key.SMOKE
    if fid in key.CANARY_PROMPTS:
        return key.CANARY_PROMPTS[fid]
    return key.BY_ID[fid].prompt


def to_clipboard(text: str) -> bool:
    """Put the words on the clipboard when pbcopy exists (macOS); report."""
    if shutil.which("pbcopy") is None:
        return False
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def from_clipboard() -> str | None:
    if shutil.which("pbpaste") is None:
        return None
    try:
        return subprocess.run(["pbpaste"], capture_output=True, check=True, timeout=10).stdout.decode("utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None


def sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^## (user|assistant) (\d+)$", line)
        if m:
            current = f"{m.group(1)} {m.group(2)}"
            out[current] = ""
        elif current:
            out[current] += line + "\n"
    return {k: v.strip() for k, v in out.items()}


def _entries(lines: list[str]) -> list[dict]:
    out = []
    for raw in lines:
        try:
            out.append(json.loads(raw))
        except ValueError:
            continue
    return out


def capture_since_mark() -> list[dict]:
    if not capture_slice.MARK.exists():
        return []
    mark = json.loads(capture_slice.MARK.read_text(encoding="utf-8"))
    return _entries(Path(mark["file"]).read_text(encoding="utf-8").splitlines()[mark["offset"] :])


def capture_before_mark() -> list[dict]:
    if not capture_slice.MARK.exists():
        return []
    mark = json.loads(capture_slice.MARK.read_text(encoding="utf-8"))
    return _entries(Path(mark["file"]).read_text(encoding="utf-8").splitlines()[: mark["offset"]])


def rel(path: Path) -> str:
    """A path as the worktree prints it, the same on every machine."""
    try:
        return path.resolve().relative_to(HERE.parent.resolve()).as_posix()
    except ValueError:
        return path.name


def unfinished() -> list[str]:
    if not LEDGER.is_dir():
        return []
    out = []
    for folder in sorted(p for p in LEDGER.iterdir() if p.is_dir() and ".attempt" not in p.name and (p / "meta.json").is_file()):
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        if not meta.get("first_answer"):
            out.append(folder.name)
    return out


def cmd_new(cid: str, app_version: str, model: str) -> int:
    if cid not in BY_ID:
        print(f"TRANSCRIPT-STOP unknown id {cid!r}; the key's ids are {[i[0] for i in IDS]}")
        return 1
    _, fid, run = BY_ID[cid]
    folder = LEDGER / cid
    if folder.exists():
        print(f"TRANSCRIPT-STOP {rel(folder)} exists; a conversation that gave a first answer is never re-run, and one before a first answer is re-run only through `abandon`")
        return 1
    if capture_slice.MARK.exists():
        print("TRANSCRIPT-STOP a mark exists; finish the conversation it belongs to first")
        return 1
    open_ids = unfinished()
    if open_ids:
        print(f"TRANSCRIPT-STOP unfinished conversation(s) {open_ids}; finish them first")
        return 1
    code = capture_slice.main(["begin"])
    if code != 0:
        return code
    before = capture_before_mark()
    initialized, _ = capture_calls(before)
    surface = capture_surface(before)
    if not initialized:
        capture_slice.MARK.unlink(missing_ok=True)
        print(f"TRANSCRIPT-STOP {key.SERVER_DID_NOT_START}: the live shim's file holds no initialize before the mark")
        return 1
    if not surface_matches_key(surface):
        capture_slice.MARK.unlink(missing_ok=True)
        print(f"TRANSCRIPT-STOP the server's surface is not the key's ({json.dumps(surface)})")
        return 1
    mark = json.loads(capture_slice.MARK.read_text(encoding="utf-8"))
    folder.mkdir(parents=True)
    meta = {
        "id": cid, "host": HOST, "fixture": fid, "repeat": run, "app_version": app_version, "model_reported": model,
        "model_reported_by": "the person, from the model picker", "app_version_by": "the person, from the About box",
        "started": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"), "ended": None,
        "minutes": None, "second_turn_sent": None, "first_answer_ends_with_question": None, "first_turn_capture_lines": None,
        "capture_initialized": initialized, "capture_surface": surface, "capture_surface_matches_key": True,
        "shim_pid": mark.get("pid"), "capture_tool_calls": None, "capture_tool_names": None,
        "prepare_feedback_calls": None, "prepare_feedback_accepted": None, "first_answer": False, "re_run_of": None,
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    (folder / "prompt.txt").write_text(prompt_for(fid) + "\n", encoding="utf-8")
    body = [f"# {cid}", f"fixture: {fid}; repeat: {run}", "", "## user 1", prompt_for(fid), "", "## assistant 1", PLACEHOLDER, ""]
    (folder / "visible.md").write_text("\n".join(body), encoding="utf-8")
    print(f"TRANSCRIPT-NEW {cid} fixture={fid} repeat={run}")
    print(f"SEND (user 1): {prompt_for(fid)}")
    print("CLIPBOARD user 1 copied; paste it into a new Desktop conversation and send" if to_clipboard(prompt_for(fid)) else "CLIPBOARD not available here; type the SEND line exactly")
    return 0


def cmd_paste(cid: str, source: str | None) -> int:
    folder = _open_conversation(cid)
    if folder is None:
        return 1
    text = Path(source).read_text(encoding="utf-8") if source else from_clipboard()
    if text is None:
        print("TRANSCRIPT-STOP no clipboard here (pbpaste); pass --from <file>")
        return 1
    if not text.strip():
        print("TRANSCRIPT-STOP the clipboard is empty; copy the reply with Desktop's copy control first")
        return 1
    secs = sections((folder / "visible.md").read_text(encoding="utf-8"))
    sent = [v for k, v in secs.items() if k.startswith("user")]
    if text.strip() in sent:
        print("TRANSCRIPT-STOP the clipboard still holds the words sent to Desktop, not the reply")
        return 1
    open_sections = [k for k, v in secs.items() if k.startswith("assistant") and v == PLACEHOLDER]
    if not open_sections:
        print("TRANSCRIPT-STOP no assistant section is open for a paste")
        return 1
    p = folder / "visible.md"
    body = p.read_text(encoding="utf-8")
    body = body.replace(PLACEHOLDER, text.rstrip("\n"), 1)
    p.write_text(body, encoding="utf-8")
    lines = text.rstrip("\n").count("\n") + 1
    print(f"PASTED {cid} {open_sections[0]} ({len(text)} chars, {lines} lines)")
    return 0


def _open_conversation(cid: str) -> Path | None:
    folder = LEDGER / cid
    if cid not in BY_ID or not (folder / "meta.json").is_file():
        print(f"TRANSCRIPT-STOP no conversation {cid} under {rel(LEDGER)}; run `new {cid}` first")
        return None
    return folder


def cmd_turn(cid: str) -> int:
    folder = _open_conversation(cid)
    if folder is None:
        return 1
    secs = sections((folder / "visible.md").read_text(encoding="utf-8"))
    first = secs.get("assistant 1", "")
    if not first or first == PLACEHOLDER:
        print("TRANSCRIPT-STOP assistant 1 is not pasted yet")
        return 1
    if BY_ID[cid][1] == "SMOKE" or BY_ID[cid][1] in key.CANARY_PROMPTS:
        print(f"TURN-NONE (the {'smoke' if BY_ID[cid][1] == 'SMOKE' else 'canary'} conversation has one turn)")
        return 0
    if "user 2" in secs:
        print("TRANSCRIPT-STOP user 2 is already written")
        return 1
    since = capture_since_mark()
    _, calls = capture_calls(since)
    accepted = bool(accepted_pf_calls(calls))
    asks = key.ends_with_question(first)
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    meta["first_answer_ends_with_question"] = asks
    meta["first_turn_capture_lines"] = len(since)
    (folder / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if not accepted and asks:
        with open(folder / "visible.md", "a", encoding="utf-8") as fh:
            fh.write(f"\n## user 2\n{key.SECOND_TURN}\n\n## assistant 2\n{PLACEHOLDER}\n")
        print("TURN-SECOND (accepted prepare_feedback call: no; first answer ends with a question: yes)")
        print(f"SEND (user 2): {key.SECOND_TURN}")
        print("CLIPBOARD user 2 copied; paste it into the same Desktop conversation and send" if to_clipboard(key.SECOND_TURN) else "CLIPBOARD not available here; type the SEND line exactly")
        return 0
    print(f"TURN-NONE (accepted prepare_feedback call: {'yes' if accepted else 'no'}; first answer ends with a question: {'yes' if asks else 'no'})")
    return 0


def cmd_finish(cid: str, minutes: float | None, re_run_of: str | None) -> int:
    folder = _open_conversation(cid)
    if folder is None:
        return 1
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    secs = sections((folder / "visible.md").read_text(encoding="utf-8"))
    missing = [k for k, v in secs.items() if not v or v == PLACEHOLDER]
    if missing:
        print(f"TRANSCRIPT-STOP section(s) not pasted: {missing}")
        return 1
    if re_run_of is not None and re_run_of not in key.TECHNICAL_FAILURES:
        print(f"TRANSCRIPT-STOP --re-run-of must be one of the key's: {list(key.TECHNICAL_FAILURES)}")
        return 1
    attempt = LEDGER / f"{cid}.attempt1"
    if attempt.exists() and re_run_of is None:
        print(f"TRANSCRIPT-STOP {rel(attempt)} exists, so this conversation is a re-run: pass --re-run-of with the abandoned attempt's reason")
        return 1
    if re_run_of is not None and not attempt.exists():
        print(f"TRANSCRIPT-STOP --re-run-of given, but no abandoned first attempt {rel(attempt)} exists")
        return 1
    live = capture_slice.live_shim_pids()
    if len(live) != 1:
        print(f"TRANSCRIPT-STOP {len(live)} live shim process(es) {live}; exactly one is expected (Desktop's, pid {meta.get('shim_pid')})")
        return 1
    if live[0] != meta.get("shim_pid"):
        print(f"TRANSCRIPT-STOP the live shim {live[0]} is not the marked one ({meta.get('shim_pid')}); Desktop restarted the server mid-conversation")
        return 1
    code = capture_slice.main(["end", str(folder)])
    if code != 0:
        return code
    entries = []
    for raw in (folder / "capture.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(raw))
        except ValueError:
            continue
    _, calls = capture_calls(entries)
    pfs = pf_calls(calls)
    accepted = [p for p in pfs if p.get("prepared") is True and p.get("message")]
    (folder / "message.txt").write_text(accepted[-1]["message"] if accepted else "", encoding="utf-8")
    if accepted:
        pasted = " ".join(" ".join(v.split()) for v in secs.values())
        labeled = [ln for ln in accepted[-1]["message"].splitlines() if ln.split(":", 1)[0].strip().lower() in ("field", "kind", "claim", "query", "rows matching")]
        if not any(" ".join(ln.split()) in pasted for ln in labeled):
            print("TRANSCRIPT-WARN none of the accepted message's labeled lines appears in the paste; check the paste belongs to this conversation")
    meta.update(
        ended=dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"), minutes=minutes,
        second_turn_sent=("user 2" in secs), capture_tool_calls=len(calls),
        capture_tool_names=[c.get("name") for c in calls],
        prepare_feedback_calls=[{k: v for k, v in p.items() if k != "message"} for p in pfs],
        prepare_feedback_accepted=len(accepted), first_answer=True, re_run_of=re_run_of,
    )
    (folder / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    with open(LEDGER / "ledger.jsonl", "a", encoding="utf-8") as fh:
        keep = ("id", "fixture", "repeat", "model_reported", "app_version", "started", "ended", "minutes", "capture_initialized",
                "capture_tool_calls", "prepare_feedback_accepted", "second_turn_sent", "re_run_of")
        fh.write(json.dumps({k: meta.get(k) for k in keep}, ensure_ascii=False) + "\n")
    print(
        f"TRANSCRIPT-OK {cid} assistant-messages {sum(1 for k in secs if k.startswith('assistant'))} tool-calls {len(calls)} "
        f"prepare_feedback {len(pfs)} accepted {len(accepted)} second-turn {meta['second_turn_sent']} minutes {minutes}"
    )
    if cid == "cd-smoke":
        ok = "list_fact_categories" in meta["capture_tool_names"]
        print("SMOKE-OK capture written, the surface is the key's, and list_fact_categories was called" if ok else "TRANSCRIPT-STOP the smoke conversation did not call list_fact_categories")
        return 0 if ok else 1
    return 0


def cmd_abandon(cid: str, reason: str | None) -> int:
    """The doors for a conversation that gave no first answer. Under one of
    the key's two technical-failure reasons it is the one re-run door: the
    conversation is kept as <id>.attempt1, the mark is released, and `new`
    may start it once more. Under the key's host-error reason (the app
    showed an error of its own before the model wrote anything) it spends
    no re-run: the conversation, and a kept first attempt if any, are kept
    under host-errors/, and `new` starts it again as a new conversation; it
    refuses when the capture since the mark holds a tool call, because then
    the model had begun to answer. Nothing is deleted."""
    folder = _open_conversation(cid)
    if folder is None:
        return 1
    host_error = reason == key.HOST_ERROR_STOP
    if reason not in key.TECHNICAL_FAILURES and not host_error:
        print(f"TRANSCRIPT-STOP --reason must be one of the key's: {list(key.TECHNICAL_FAILURES) + [key.HOST_ERROR_STOP]}")
        return 1
    secs = sections((folder / "visible.md").read_text(encoding="utf-8"))
    if any(k.startswith("assistant") and v and v != PLACEHOLDER for k, v in secs.items()):
        print(f"TRANSCRIPT-STOP {cid} has a pasted answer; a conversation that gave a first answer is never re-run")
        return 1
    attempt = LEDGER / f"{cid}.attempt1"
    if host_error:
        _, calls = capture_calls(capture_since_mark())
        if calls:
            print(f"TRANSCRIPT-STOP {cid}: the capture holds {len(calls)} tool call(s) since the mark, so the model had begun to answer; this goes to the Architect")
            return 1
    elif attempt.exists():
        print(f"TRANSCRIPT-STOP {rel(attempt)} exists; the key allows one re-run per conversation")
        return 1
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    if capture_slice.MARK.exists():
        mark = json.loads(capture_slice.MARK.read_text(encoding="utf-8"))
        if mark.get("pid") == meta.get("shim_pid"):
            code = capture_slice.main(["end", str(folder)])
            if code != 0:
                return code
        else:
            print("TRANSCRIPT-STOP the mark belongs to another conversation")
            return 1
    meta.update(abandoned=True, abandoned_reason=reason, ended=dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"))
    (folder / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if host_error:
        root = LEDGER / "host-errors"
        root.mkdir(parents=True, exist_ok=True)
        n = 1
        while (root / f"{cid}-{n}").exists() or (root / f"{cid}-{n}.attempt1").exists():
            n += 1
        dest = root / f"{cid}-{n}"
        if attempt.exists():
            attempt.rename(root / f"{dest.name}.attempt1")
        folder.rename(dest)
        print(f"TRANSCRIPT-HOST-ERROR {cid} kept as {rel(dest)} ({reason}); no re-run is spent; fix the host, then `new {cid}` starts it again")
        return 0
    folder.rename(attempt)
    print(f"TRANSCRIPT-ABANDONED {cid} kept as {rel(attempt)} ({reason}); `new {cid}` may run once more, and its `finish` passes --re-run-of with this reason")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["new", "paste", "turn", "finish", "abandon", "ids"])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--app-version", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--minutes", type=float, default=None)
    ap.add_argument("--re-run-of", default=None)
    ap.add_argument("--reason", default=None)
    ap.add_argument("--from", dest="source", default=None)
    a = ap.parse_args(argv)
    if a.command == "ids":
        for i in IDS:
            print(i[0])
        return 0
    if not a.id:
        print("TRANSCRIPT-STOP an id is required")
        return 2
    if a.command == "new":
        if not (a.app_version and a.model):
            print("TRANSCRIPT-STOP new needs --app-version and --model (read from Desktop's About box and the model picker)")
            return 2
        return cmd_new(a.id, a.app_version, a.model)
    if a.command == "paste":
        return cmd_paste(a.id, a.source)
    if a.command == "turn":
        return cmd_turn(a.id)
    if a.command == "abandon":
        return cmd_abandon(a.id, a.reason)
    return cmd_finish(a.id, a.minutes, a.re_run_of)


if __name__ == "__main__":
    sys.exit(main())
