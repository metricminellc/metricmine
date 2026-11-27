"""The Desktop protocol's guards, against a live shim held open the way
Desktop holds one: the mark, the turn rule, finish, the one re-run door,
and the stops. Needs the pinned served file."""

import json
import os
import subprocess
import sys
import tempfile
import time

import pytest
from conftest import E1T

sys.path.insert(0, str(E1T))
import capture_slice  # noqa: E402
import key  # noqa: E402
import transcript  # noqa: E402

SHIM = E1T / "capture_shim.py"
CRASH = key.TECHNICAL_FAILURES[0]
F1_ARGS = {
    "field": "invoice_lines.quantity", "kind": "rule_wanted",
    "claim": "A flag that marks stock-adjustment lines is wanted.",
    "query": "select * from gold.mart_invoice_lines_typed where not is_cancellation and quantity < 0",
}


AGENT_MODE = "local-agent-mode-metricmine-gold"


class Host:
    """A client that holds one shim open across protocol calls. It names
    itself as Desktop's chat does (`claude-ai`) unless told otherwise;
    Desktop 6.28899.6's local agent mode opens a second connection under
    its own name and asks for tools only (measured November 27, 2026)."""

    def __init__(self, pinned, cap, client=capture_slice.CHAT_CLIENT):
        env = dict(os.environ, MM_SERVE_DB=str(pinned), MM_E1T_CAPTURE=str(cap))
        self.proc = subprocess.Popen([sys.executable, str(SHIM)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env, cwd=tempfile.gettempdir())
        self.n = 0
        version = "0.1.0" if client == capture_slice.CHAT_CLIENT else "1.0.0"
        self.send("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": client, "version": version}})
        self.proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n')
        self.proc.stdin.flush()
        self.send("tools/list", {})
        time.sleep(0.3)

    def send(self, method, params):
        self.n += 1
        self.proc.stdin.write((json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params}) + "\n").encode())
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())

    def call(self, name, args):
        return self.send("tools/call", {"name": name, "arguments": args})

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=10)


def paste(folder, text):
    p = folder / "visible.md"
    p.write_text(p.read_text(encoding="utf-8").replace(transcript.PLACEHOLDER, text, 1), encoding="utf-8")


@pytest.fixture
def protocol(pinned, tmp_path, monkeypatch):
    cap = tmp_path / "cap"
    monkeypatch.setenv("MM_E1T_CAPTURE", str(cap))
    monkeypatch.setattr(capture_slice, "MARK", tmp_path / "MARK.json")
    monkeypatch.setattr(transcript, "LEDGER", tmp_path / "ledger" / "claude-desktop")
    host = Host(pinned, cap)
    host.pinned, host.cap = pinned, cap
    yield host
    if host.proc.poll() is None:
        host.close()


def test_the_live_shim_search_counts_interpreters_and_never_a_shell_that_names_the_file(protocol):
    bystander = subprocess.Popen(["bash", "-c", "sleep 20; true # e1t/capture_shim.py"])  # the shell stays, its line naming the file
    try:
        time.sleep(0.3)
        live = capture_slice.live_shim_pids()
        assert protocol.proc.pid in live and bystander.pid not in live
    finally:
        bystander.kill()
        bystander.wait()


def test_the_live_shim_pattern_reads_every_interpreter_form_and_never_a_shell():
    """No pinned file and no process: the `ps` rows each platform prints,
    held to the pattern. The framework form is the Mac of record's
    (November 25, 2026): its venv's python3.12 is a launcher that starts
    Python.app's capital-P image, so `ps` never shows a lowercase python."""
    shim = "/Users/u/code/metricmine/e1t/capture_shim.py"
    for row in (
        f"/home/u/code/metricmine/.venv/bin/python {shim}",
        f"/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python {shim}",
        f"/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 {shim}",
        f"/Users/u/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12 {shim}",
        f"python3 -u {shim}",
    ):
        assert capture_slice.SHIM_ARGS.match(row), row
    for row in (
        "bash -c sleep 20 # e1t/capture_shim.py",
        "/bin/zsh -c uv run python e1t/capture_slice.py begin",
        "/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python -m metricmine.server",
        "/usr/bin/python3 -m metricmine.server",
        f"/usr/bin/python3 {shim}.bak",
        f"vim {shim}",
    ):
        assert not capture_slice.SHIM_ARGS.match(row), row


def test_the_ids_are_the_smoke_the_canary_s_two_and_nine_fixture_conversations(capsys):
    assert transcript.main(["ids"]) == 0
    ids = capsys.readouterr().out.split()
    assert ids[:3] == ["cd-smoke", "cd-C1", "cd-C2"] and len(ids) == 12
    assert transcript.prompt_for("C1") == key.CANARY_PROMPTS["C1"] and transcript.prompt_for("SMOKE") == key.SMOKE


def test_new_turn_and_finish_follow_the_key_s_rules(protocol, capsys):
    assert transcript.main(["new", "cd-C1", "--app-version", "t", "--model", "m"]) == 0
    paste(transcript.LEDGER / "cd-C1", "The server sent me no instructions.")
    assert transcript.main(["turn", "cd-C1"]) == 0
    assert "TURN-NONE (the canary conversation has one turn)" in capsys.readouterr().out
    assert transcript.main(["finish", "cd-C1", "--minutes", "1"]) == 0
    assert transcript.main(["new", "cd-smoke", "--app-version", "t", "--model", "m"]) == 0
    assert transcript.main(["new", "cd-F1-r1", "--app-version", "t", "--model", "m"]) == 1  # a mark exists
    protocol.call("list_fact_categories", {})
    folder = transcript.LEDGER / "cd-smoke"
    assert transcript.main(["finish", "cd-smoke"]) == 1  # not pasted
    paste(folder, "Three categories.")
    assert transcript.main(["turn", "cd-smoke"]) == 0
    assert transcript.main(["finish", "cd-smoke", "--minutes", "1"]) == 0
    out = capsys.readouterr().out
    assert "SMOKE-OK" in out and "TRANSCRIPT-OK cd-smoke" in out
    # a printed path is the worktree's own form, the same on every machine
    assert transcript.rel(transcript.HERE / "ledger" / "claude-desktop" / "x") == "e1t/ledger/claude-desktop/x"
    assert capture_slice.rel(capture_slice.HERE / "capture") == "e1t/capture"
    # F1: an accepted call in the first turn, no second turn
    assert transcript.main(["new", "cd-F1-r1", "--app-version", "t", "--model", "m"]) == 0
    msg = protocol.call("prepare_feedback", F1_ARGS)["result"]["structuredContent"]["message"]
    paste(transcript.LEDGER / "cd-F1-r1", "Here it is:\n" + msg)
    assert transcript.main(["turn", "cd-F1-r1"]) == 0
    assert "TURN-NONE (accepted prepare_feedback call: yes" in capsys.readouterr().out
    assert transcript.main(["finish", "cd-F1-r1", "--minutes", "2"]) == 0
    meta = json.loads((transcript.LEDGER / "cd-F1-r1" / "meta.json").read_text())
    assert meta["prepare_feedback_accepted"] == 1 and meta["second_turn_sent"] is False
    assert (transcript.LEDGER / "cd-F1-r1" / "message.txt").read_text(encoding="utf-8") == msg
    # F2: no accepted call and a question: the fixed second turn
    assert transcript.main(["new", "cd-F2-r1", "--app-version", "t", "--model", "m"]) == 0
    protocol.call("get_context", {"category": "flights"})
    paste(transcript.LEDGER / "cd-F2-r1", "Do you want me to use the tool?")
    assert transcript.main(["turn", "cd-F2-r1"]) == 0
    out = capsys.readouterr().out
    assert "TURN-SECOND" in out and key.SECOND_TURN in out
    assert transcript.main(["turn", "cd-F2-r1"]) == 1  # user 2 already written
    assert transcript.main(["finish", "cd-F2-r1"]) == 1  # assistant 2 not pasted
    paste(transcript.LEDGER / "cd-F2-r1", "I could not.")
    assert transcript.main(["finish", "cd-F2-r1", "--minutes", "3"]) == 0
    meta = json.loads((transcript.LEDGER / "cd-F2-r1" / "meta.json").read_text())
    assert meta["second_turn_sent"] is True and meta["first_turn_capture_lines"] == 2
    assert transcript.main(["new", "cd-F2-r1", "--app-version", "t", "--model", "m"]) == 1  # never re-run
    assert transcript.main(["turn", "cd-F3-r9"]) == 1 and transcript.main(["finish", "cd-F3-r1"]) == 1  # unknown, not started


def test_the_one_re_run_door(protocol, capsys):
    assert transcript.main(["new", "cd-F3-r1", "--app-version", "t", "--model", "m"]) == 0
    assert transcript.main(["abandon", "cd-F3-r1", "--reason", "it broke"]) == 1
    protocol.close()  # the host crashed before a first answer
    assert transcript.main(["finish", "cd-F3-r1"]) == 1
    assert transcript.main(["abandon", "cd-F3-r1", "--reason", CRASH]) == 0
    assert (transcript.LEDGER / "cd-F3-r1.attempt1" / "capture.jsonl").is_file() and not capture_slice.MARK.exists()
    assert json.loads((transcript.LEDGER / "cd-F3-r1.attempt1" / "meta.json").read_text())["abandoned_reason"] == CRASH
    assert transcript.main(["new", "cd-F3-r1", "--app-version", "t", "--model", "m"]) == 1  # no live shim
    again = Host(protocol.pinned, protocol.cap)
    try:
        assert transcript.main(["new", "cd-F3-r1", "--app-version", "t", "--model", "m"]) == 0  # the attempt does not block
        paste(transcript.LEDGER / "cd-F3-r1", "Nothing to report.")
        assert transcript.main(["finish", "cd-F3-r1"]) == 1  # a re-run must say so
        assert transcript.main(["finish", "cd-F3-r1", "--re-run-of", CRASH]) == 0
        assert transcript.main(["abandon", "cd-F3-r1", "--reason", CRASH]) == 1  # a pasted answer
        assert transcript.main(["new", "cd-F1-r1", "--app-version", "t", "--model", "m"]) == 0
        paste(transcript.LEDGER / "cd-F1-r1", "An answer.")
        assert transcript.main(["finish", "cd-F1-r1", "--re-run-of", CRASH]) == 1  # no attempt exists
        out = capsys.readouterr().out
        assert "TRANSCRIPT-ABANDONED cd-F3-r1" in out and "no abandoned first attempt" in out
    finally:
        again.close()


def test_paste_writes_the_reply_from_a_file_and_refuses_the_sent_words(protocol, tmp_path, capsys):
    assert transcript.main(["new", "cd-F1-r1", "--app-version", "t", "--model", "m"]) == 0
    sent = tmp_path / "sent.txt"
    sent.write_text(key.BY_ID["F1"].prompt + "\n", encoding="utf-8")
    assert transcript.main(["paste", "cd-F1-r1", "--from", str(sent)]) == 1  # the words sent, not the reply
    empty = tmp_path / "empty.txt"
    empty.write_text("  \n", encoding="utf-8")
    assert transcript.main(["paste", "cd-F1-r1", "--from", str(empty)]) == 1
    reply = tmp_path / "reply.txt"
    reply.write_text("Here it is.\n\nFEEDBACK\nfield: x\nEND FEEDBACK\n", encoding="utf-8")
    assert transcript.main(["paste", "cd-F1-r1", "--from", str(reply)]) == 0
    assert transcript.main(["paste", "cd-F1-r1", "--from", str(reply)]) == 1  # no open section
    out = capsys.readouterr().out
    assert "PASTED cd-F1-r1 assistant 1 (" in out and "still holds the words sent" in out and "no assistant section is open" in out
    secs = transcript.sections((transcript.LEDGER / "cd-F1-r1" / "visible.md").read_text(encoding="utf-8"))
    assert secs["assistant 1"] == "Here it is.\n\nFEEDBACK\nfield: x\nEND FEEDBACK"
    assert transcript.main(["turn", "cd-F1-r1"]) == 0
    assert transcript.main(["finish", "cd-F1-r1", "--minutes", "1"]) == 0


def test_a_server_restarted_mid_conversation_is_a_stop(protocol, capsys):
    assert transcript.main(["new", "cd-F1-r1", "--app-version", "t", "--model", "m"]) == 0
    paste(transcript.LEDGER / "cd-F1-r1", "An answer.")
    protocol.close()
    again = Host(protocol.pinned, protocol.cap)
    try:
        assert transcript.main(["finish", "cd-F1-r1"]) == 1
        assert "restarted the server mid-conversation" in capsys.readouterr().out
    finally:
        again.close()


def test_a_shim_that_never_initialized_is_a_stop(protocol, capsys):
    protocol.close()
    env = dict(os.environ, MM_SERVE_DB=str(protocol.pinned), MM_E1T_CAPTURE=str(protocol.cap))
    idle = subprocess.Popen([sys.executable, str(SHIM)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env, cwd=tempfile.gettempdir())
    try:
        time.sleep(0.5)
        assert transcript.main(["new", "cd-F1-r1", "--app-version", "t", "--model", "m"]) == 1
        assert key.SERVER_DID_NOT_START in capsys.readouterr().out and not capture_slice.MARK.exists()
    finally:
        idle.stdin.close()
        idle.wait(timeout=10)


def test_the_host_error_door_spends_no_re_run_and_refuses_once_the_model_called_a_tool(protocol, capsys):
    """The app's own error before the model wrote anything: the attempt is
    kept under host-errors/, no re-run is spent, and `new` starts the
    conversation again; after a tool call, the door refuses."""
    assert transcript.main(["new", "cd-F1-r1", "--app-version", "t", "--model", "m"]) == 0
    assert transcript.main(["abandon", "cd-F1-r1", "--reason", "it broke"]) == 1
    assert key.HOST_ERROR_STOP in capsys.readouterr().out  # the reasons the door takes are named
    assert transcript.main(["abandon", "cd-F1-r1", "--reason", key.HOST_ERROR_STOP]) == 0
    out = capsys.readouterr().out
    assert "TRANSCRIPT-HOST-ERROR cd-F1-r1 kept as " in out and "no re-run is spent" in out
    aside = transcript.LEDGER / "host-errors" / "cd-F1-r1-1"
    assert json.loads((aside / "meta.json").read_text())["abandoned_reason"] == key.HOST_ERROR_STOP and not capture_slice.MARK.exists()
    assert transcript.main(["new", "cd-F1-r1", "--app-version", "t", "--model", "m"]) == 0  # starts again
    paste(transcript.LEDGER / "cd-F1-r1", "Nothing to report.")
    assert transcript.main(["finish", "cd-F1-r1", "--minutes", "1"]) == 0  # no --re-run-of: no re-run was spent
    assert transcript.main(["new", "cd-F2-r1", "--app-version", "t", "--model", "m"]) == 0
    protocol.call("list_fact_categories", {})
    assert transcript.main(["abandon", "cd-F2-r1", "--reason", key.HOST_ERROR_STOP]) == 1
    assert "had begun to answer" in capsys.readouterr().out and (transcript.LEDGER / "cd-F2-r1").is_dir()


def test_desktop_s_two_connections_slice_the_chat_and_watch_the_agent_mode(protocol, capsys):
    """Desktop 6.28899.6 holds two shims for one entry: its chat and its
    local agent mode. The mark takes the chat's file and records the
    other; a conversation whose calls stay on the chat finishes; a tool
    call on the other connection since the mark stops the slice, leaves
    the mark, and writes nothing. Two chat connections are a stop."""
    agent = Host(protocol.pinned, protocol.cap, client=AGENT_MODE)
    try:
        assert capture_slice.client_of(capture_slice.file_for_pid(agent.proc.pid)) == AGENT_MODE
        assert capture_slice.chat_candidates(capture_slice.live_shims()) == [protocol.proc.pid]
        assert transcript.main(["new", "cd-smoke", "--app-version", "t", "--model", "m"]) == 0
        out = capsys.readouterr().out
        assert f"(shim pid {protocol.proc.pid})" in out
        meta = json.loads((transcript.LEDGER / "cd-smoke" / "meta.json").read_text())
        assert meta["shim_client"] == capture_slice.CHAT_CLIENT
        assert meta["shims_watched"] == [{"pid": agent.proc.pid, "client": AGENT_MODE}]
        protocol.call("list_fact_categories", {})
        paste(transcript.LEDGER / "cd-smoke", "Three categories.")
        assert transcript.main(["turn", "cd-smoke"]) == 0
        assert transcript.main(["finish", "cd-smoke", "--minutes", "1"]) == 0
        out = capsys.readouterr().out
        assert "TRANSCRIPT-OK cd-smoke" in out and "SMOKE-OK" in out and "tools/call: 1 ['list_fact_categories']" in out
        # the conversation's call reaches the agent mode's connection
        assert transcript.main(["new", "cd-C1", "--app-version", "t", "--model", "m"]) == 0
        agent.call("list_fact_categories", {})
        paste(transcript.LEDGER / "cd-C1", "The server sent me no instructions.")
        assert transcript.main(["finish", "cd-C1", "--minutes", "1"]) == 1
        out = capsys.readouterr().out
        assert "SLICE-STOP: tool call(s) since the mark reached another connection: " in out and f"({AGENT_MODE}) 1" in out
        assert capture_slice.MARK.exists() and not (transcript.LEDGER / "cd-C1" / "capture.jsonl").exists()
        assert json.loads((transcript.LEDGER / "cd-C1" / "meta.json").read_text())["first_answer"] is False
        capture_slice.MARK.unlink()
        # a second chat connection: no shim can be chosen
        second = Host(protocol.pinned, protocol.cap)
        try:
            assert capture_slice.main(["begin"]) == 1
            out = capsys.readouterr().out
            assert "SLICE-STOP: 2 live shim process(es) " in out and f"{agent.proc.pid} {AGENT_MODE}" in out
            assert not capture_slice.MARK.exists()
        finally:
            second.close()
    finally:
        agent.close()


def test_the_turn_rule_stops_when_a_call_reached_another_connection(protocol, capsys):
    """The turn rule reads only the chat's capture, so a first turn whose
    accepted call reached another connection is a stop before anything is
    decided, never a second turn. A shim still starting beside the named
    chat is not a second candidate."""
    agent = Host(protocol.pinned, protocol.cap, client=AGENT_MODE)
    env = dict(os.environ, MM_SERVE_DB=str(protocol.pinned), MM_E1T_CAPTURE=str(protocol.cap))
    starting = subprocess.Popen([sys.executable, str(SHIM)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env, cwd=tempfile.gettempdir())
    try:
        time.sleep(0.5)
        assert capture_slice.chat_candidates(capture_slice.live_shims()) == [protocol.proc.pid]
        assert transcript.main(["new", "cd-F1-r1", "--app-version", "t", "--model", "m"]) == 0
        msg = agent.call("prepare_feedback", F1_ARGS)["result"]["structuredContent"]["message"]
        paste(transcript.LEDGER / "cd-F1-r1", "Do you want me to send this?\n" + msg + "\nShall I?")
        capsys.readouterr()
        assert transcript.main(["turn", "cd-F1-r1"]) == 1
        out = capsys.readouterr().out
        assert out.startswith("TRANSCRIPT-STOP tool call(s) since the mark reached another connection: ") and "TURN-" not in out
        assert "## user 2" not in (transcript.LEDGER / "cd-F1-r1" / "visible.md").read_text(encoding="utf-8")
    finally:
        starting.stdin.close()
        starting.wait(timeout=10)
        agent.close()


def test_the_re_run_door_stops_when_a_restarted_chat_server_took_a_call(protocol, capsys):
    """After the chat's server crashed and Desktop restarted it, a call on
    the new server since the mark means the record would be split: the
    re-run door stops, keeps nothing, and the mark stands."""
    assert transcript.main(["new", "cd-F3-r1", "--app-version", "t", "--model", "m"]) == 0
    protocol.close()  # the chat server crashed
    again = Host(protocol.pinned, protocol.cap)  # Desktop restarted it
    try:
        again.call("list_fact_categories", {})
        capsys.readouterr()
        assert transcript.main(["abandon", "cd-F3-r1", "--reason", CRASH]) == 1
        assert "SLICE-STOP: tool call(s) since the mark reached another connection: " in capsys.readouterr().out
        assert capture_slice.MARK.exists() and not (transcript.LEDGER / "cd-F3-r1.attempt1").exists()
    finally:
        again.close()


def test_a_shim_writing_under_another_capture_folder_is_never_read(protocol, tmp_path, capsys):
    """Desktop's shims during a sitting, another worktree's, or a test's:
    a live shim whose file is not under this capture folder is neither a
    candidate nor watched, so the mark and the slice are this folder's."""
    elsewhere = Host(protocol.pinned, tmp_path / "elsewhere")
    try:
        assert elsewhere.proc.pid in capture_slice.live_shim_pids()
        assert [pid for pid, _, _ in capture_slice.live_shims()] == [protocol.proc.pid]
        assert transcript.main(["new", "cd-C1", "--app-version", "t", "--model", "m"]) == 0
        elsewhere.call("list_fact_categories", {})
        paste(transcript.LEDGER / "cd-C1", "The server sent me no instructions.")
        assert transcript.main(["finish", "cd-C1", "--minutes", "1"]) == 0
        assert "TRANSCRIPT-OK cd-C1" in capsys.readouterr().out
    finally:
        elsewhere.close()


def test_the_agent_mode_s_earlier_calls_never_stop_a_later_conversation(protocol, capsys):
    """A tool call on the other connection before the mark is not this
    conversation's: the slice reads only what came after the mark."""
    agent = Host(protocol.pinned, protocol.cap, client=AGENT_MODE)
    try:
        agent.call("list_fact_categories", {})
        time.sleep(0.05)
        assert transcript.main(["new", "cd-C1", "--app-version", "t", "--model", "m"]) == 0
        paste(transcript.LEDGER / "cd-C1", "The server sent me no instructions.")
        assert transcript.main(["finish", "cd-C1", "--minutes", "1"]) == 0
        assert "TRANSCRIPT-OK cd-C1" in capsys.readouterr().out
    finally:
        agent.close()
