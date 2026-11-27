"""The driver's pure parts: the plan, the command line, the stream reader,
the capture reader, the scrubber, the host's own error read per call, the
sweep, and the smoke guard; and the batch path against a stand-in host
that prints streams built in the shape of the measured signed-out
stream. Nothing here runs Claude Code."""

import json
import os
import sys
from pathlib import Path

from conftest import E1T

sys.path.insert(0, str(E1T))
import driver  # noqa: E402
import key  # noqa: E402


def test_the_plan_names_every_conversation_once():
    fx = driver.plan("fixtures", 5)
    assert len(fx) == 15 and len({c[0] for c in fx}) == 15 and fx[0][0] == "cc-F1-r1" and fx[-1][0] == "cc-F3-r5"
    ct = driver.plan("controls", 3)
    assert len(ct) == 9 and ct[0][0] == "cc-P2-r1"
    assert [c[0] for c in driver.plan("canary", 0)] == ["cc-C1", "cc-C2"]
    assert driver.plan("smoke", 0)[0][2] == key.SMOKE


def test_the_command_line_isolates_the_host_and_names_the_model():
    cmd = driver.command("hello", Path("/tmp/mcp.json"), "sonnet", None)
    assert cmd[:3] == ["claude", "-p", "hello"]
    assert "--strict-mcp-config" in cmd and cmd[cmd.index("--tools") + 1] == ""
    assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk" and cmd[cmd.index("--model") + 1] == "sonnet"
    allowed = cmd[cmd.index("--allowedTools") + 1 : cmd.index("--permission-mode")]
    assert allowed == [f"mcp__metricmine-gold__{t}" for t in driver.SERVER_TOOLS] and len(allowed) == 6
    assert cmd[cmd.index("--max-turns") + 1] == str(key.MAX_TURNS)
    assert cmd[cmd.index("--max-budget-usd") + 1] == str(key.PER_TURN_BUDGET_USD)
    assert cmd[cmd.index("--setting-sources") + 1] == ""
    assert "--resume" not in cmd and driver.command("x", Path("m"), "sonnet", "abc")[-2:] == ["--resume", "abc"]


STREAM = [
    {"type": "system", "subtype": "init", "model": "claude-sonnet-5-5", "cwd": "/x", "tools": ["mcp__metricmine-gold__query"], "mcp_servers": [{"name": "metricmine-gold", "status": "connected"}], "permissionMode": "dontAsk", "claude_code_version": "2.1.316", "session_id": "s1"},
    {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Let me prepare it."}, {"type": "tool_use", "id": "t1", "name": "mcp__metricmine-gold__prepare_feedback", "input": {"field": "invoice_lines.quantity"}}]}},
    {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "{...}"}]}]}},
    {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Here is the message:\nFEEDBACK\nfield: a.b\nEND FEEDBACK"}]}},
    {"type": "result", "subtype": "success", "is_error": False, "duration_ms": 1200, "num_turns": 2, "result": "Here is the message:", "session_id": "s1", "total_cost_usd": 0.0123, "modelUsage": {"claude-sonnet-5-5": {"inputTokens": 10}}},
]


def test_the_stream_reader_finds_the_init_the_text_the_tool_uses_and_the_result():
    assert driver.init_of(STREAM)["model"] == "claude-sonnet-5-5"
    assert driver.visible_text(STREAM) == "Let me prepare it.\n\nHere is the message:\nFEEDBACK\nfield: a.b\nEND FEEDBACK"
    assert [u["name"] for u in driver.host_tool_uses(STREAM)] == ["mcp__metricmine-gold__prepare_feedback"]
    r = driver.result_of(STREAM)
    assert r["session_id"] == "s1" and r["total_cost_usd"] == 0.0123
    assert driver.visible_text([STREAM[-1]]) == "Here is the message:"


def capture_lines(calls: list[tuple[str, dict, dict]]) -> list[dict]:
    """Shim-shaped entries: an initialize pair, then each (name, arguments, result)."""
    out = [
        {"t": "2026-11-02T00:00:00.000+00:00", "dir": "client", "line": json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})},
        {"t": "2026-11-02T00:00:00.100+00:00", "dir": "server", "line": json.dumps({"jsonrpc": "2.0", "id": 0, "result": {"instructions": "x", "serverInfo": {"name": "metricmine-gold", "version": "1.3.0"}}})},
    ]
    for i, (name, args, result) in enumerate(calls, start=1):
        out.append({"t": f"2026-11-02T00:00:0{i}.000+00:00", "dir": "client", "line": json.dumps({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}})})
        out.append({"t": f"2026-11-02T00:00:0{i}.500+00:00", "dir": "server", "line": json.dumps({"jsonrpc": "2.0", "id": i, "result": result})})
    return out


def test_the_capture_reader_pairs_calls_with_results_and_reads_prepare_feedback():
    refused = {"structuredContent": {"prepared": False, "reason": "kind 'x' is outside the six", "remedy": "use one of ...", "message": None}}
    accepted = {"structuredContent": {"prepared": True, "message": "FEEDBACK\nfield: invoice_lines.quantity\nEND FEEDBACK\n", "rows_matching": 90}}
    entries = capture_lines([
        ("list_fact_categories", {}, {"structuredContent": {"categories": []}}),
        ("prepare_feedback", {"field": "invoice_lines.quantity", "kind": "x", "claim": "c", "query": "q"}, refused),
        ("prepare_feedback", {"field": "invoice_lines.quantity", "kind": "rule_wanted", "claim": "c", "query": "q"}, accepted),
    ])
    initialized, calls = driver.capture_calls(entries)
    assert initialized and [c["name"] for c in calls] == ["list_fact_categories", "prepare_feedback", "prepare_feedback"]
    pfs = driver.pf_calls(calls)
    assert [p["prepared"] for p in pfs] == [False, True] and pfs[1]["rows_matching"] == 90 and pfs[1]["kind"] == "rule_wanted"
    assert pfs[0]["reason"].startswith("kind 'x'")
    # a union-wrapped structuredContent ({"result": {...}}) is unwrapped too
    wrapped = {"structuredContent": {"result": {"prepared": True, "message": "m", "rows_matching": 1}}}
    pfs2 = driver.pf_calls(driver.capture_calls(capture_lines([("prepare_feedback", {"field": "a.b", "kind": "rule_wanted"}, wrapped)]))[1])
    assert pfs2[0]["prepared"] is True and pfs2[0]["message"] == "m"


def test_the_conditions_record_names_what_is_dirty_outside_the_ledger(tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "a.txt"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "a"], check=True)
    assert driver.conditions(tmp_path)["worktree_dirty_outside_ledger"] == []
    (tmp_path / "prep-e1t").mkdir()
    (tmp_path / "prep-e1t" / "x").write_text("x", encoding="utf-8")
    (tmp_path / "e1t" / "ledger" / "claude-code").mkdir(parents=True)
    (tmp_path / "e1t" / "ledger" / "claude-code" / "y").write_text("y", encoding="utf-8")
    assert driver.conditions(tmp_path)["worktree_dirty_outside_ledger"] == ["prep-e1t/"]
    (tmp_path / "a.txt").write_text("changed", encoding="utf-8")  # a modified tracked file: " M a.txt", leading space
    assert driver.conditions(tmp_path)["worktree_dirty_outside_ledger"] == ["a.txt", "prep-e1t/"]


def test_the_scrubber_replaces_this_machine_s_paths(tmp_path):
    worktree = tmp_path / "wt"
    served = tmp_path / "served.duckdb"
    worktree.mkdir()
    served.write_bytes(b"x")
    scrub = driver.Scrubber(worktree, served)
    text = f"cwd {worktree} file {served} home {Path.home()} other"
    out = scrub(text)
    assert str(worktree) not in out and str(served) not in out and str(Path.home()) not in out
    assert "<worktree>" in out and "<served>" in out and "<home>" in out
    dashed = str(worktree).replace("/", "-")
    assert scrub(f"memory at {dashed}/memory") == "memory at <worktree>/memory"


def test_the_capture_surface_is_read_from_the_handshake_and_compared_to_the_key():
    instructions = "x" * key.INSTRUCTIONS_LENGTH
    entries = [
        {"t": "a", "dir": "server", "line": json.dumps({"jsonrpc": "2.0", "id": 0, "result": {"instructions": instructions, "serverInfo": {}}})},
        {"t": "b", "dir": "server", "line": json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": n} for n in driver.SERVER_TOOLS]}})},
    ]
    surface = driver.capture_surface(entries)
    assert surface["instructions_length"] == key.INSTRUCTIONS_LENGTH and len(surface["tools"]) == 6
    assert not driver.surface_matches_key(surface)  # the digest is not the key's
    surface["instructions_sha256"] = key.INSTRUCTIONS_SHA256
    assert driver.surface_matches_key(surface)
    assert not driver.surface_matches_key(dict(surface, tools=surface["tools"][:5]))


# The host's own error, in the shape Claude Code 2.1.311 printed signed
# out (the sandbox, November 25, 2026), with the text the Mac of record
# printed the same day with an expired sign-in, trimmed to the fields the
# driver reads. The other streams are built in that shape; the limit's
# words are a phrase the 2.1.311 binary composes (read in its code, not
# measured live).
HOST_ERROR_TEXT = "Failed to authenticate: OAuth session expired and could not be refreshed"
LIMIT_TEXT = "You've hit your limit"


def _init(version="2.1.311"):
    return {"type": "system", "subtype": "init", "model": "claude-sonnet-5-5", "claude_code_version": version, "apiKeySource": "none", "permissionMode": "dontAsk", "tools": [f"mcp__metricmine-gold__{t}" for t in driver.SERVER_TOOLS], "mcp_servers": [{"name": "metricmine-gold", "status": "connected"}], "session_id": "s0"}


def _host(text):
    return {"type": "assistant", "message": {"model": "<synthetic>", "role": "assistant", "content": [{"type": "text", "text": text}]}, "error": "authentication_failed", "session_id": "s0"}


def _model(content):
    return {"type": "assistant", "message": {"model": "claude-sonnet-5-5", "role": "assistant", "content": content}, "session_id": "s0"}


def _result(is_error, usage, text, subtype="success"):
    return {"type": "result", "subtype": subtype, "is_error": is_error, "num_turns": 1, "total_cost_usd": 0.01 if usage else 0, "modelUsage": usage, "result": text, "session_id": "s0"}


USED = {"claude-sonnet-5-5": {"inputTokens": 10}}
HOST_ERROR_STREAM = [_init(), _host(HOST_ERROR_TEXT), _result(True, {}, HOST_ERROR_TEXT)]
AFTER_TOOL = [_init(), _model([{"type": "tool_use", "id": "t1", "name": "mcp__metricmine-gold__get_context", "input": {}}]), _host(LIMIT_TEXT), _result(True, USED, LIMIT_TEXT)]
ASKS = [_init(), _model([{"type": "text", "text": "Which kind do you mean?"}]), _result(False, USED, "Which kind do you mean?")]
TURN2_ERROR = [_init(), _host(LIMIT_TEXT), _result(True, USED, LIMIT_TEXT)]  # a resumed call carries the earlier usage
ANSWER = [_init(), _model([{"type": "text", "text": "Here is the message."}]), _result(False, USED, "Here is the message.")]


def test_the_host_s_own_error_is_read_per_call_and_is_never_an_answer():
    assert driver.host_error(HOST_ERROR_STREAM) == HOST_ERROR_TEXT and not driver.model_wrote(HOST_ERROR_STREAM)
    assert driver.visible_text(HOST_ERROR_STREAM) == ""
    assert driver.host_error(AFTER_TOOL) == LIMIT_TEXT and driver.model_wrote(AFTER_TOOL)
    assert driver.host_error(TURN2_ERROR) == LIMIT_TEXT and not driver.model_wrote(TURN2_ERROR)
    crash = [_init(), _model([{"type": "text", "text": "Let me look."}]), _host("Claude Code exited"), _result(True, {}, "", "error_during_execution")]
    assert driver.host_error(crash) == "Claude Code exited" and driver.model_wrote(crash) and driver.visible_text(crash) == "Let me look."
    for cap in ("error_max_turns", "error_max_budget_usd"):  # the key's own bounds: the model's conversation
        assert driver.host_error(STREAM[:-1] + [dict(STREAM[-1], subtype=cap, is_error=True)]) is None
        assert driver.host_error([_init(), _result(True, USED, "", cap)]) is None  # even with no assistant event
    reasoning = [_init(), _model([{"type": "thinking", "thinking": "..."}]), _host(HOST_ERROR_TEXT), _result(True, USED, HOST_ERROR_TEXT)]
    assert driver.host_error(reasoning) == HOST_ERROR_TEXT and not driver.model_wrote(reasoning)  # a reasoning step is not writing
    bare = [_init(), _result(True, {}, "an exit before any message", "error_during_execution")]
    assert driver.host_error(bare) == "an exit before any message" and not driver.model_wrote(bare)
    assert driver.host_error(STREAM) is None and driver.host_error([]) is None
    assert driver.meta_is_set_aside({"is_error": True, "models_used": [], "capture_tool_calls": 0})  # recorded before the rule
    assert not driver.meta_is_set_aside({"is_error": True, "models_used": [], "capture_tool_calls": 1})
    assert not driver.meta_is_set_aside({"is_error": True, "models_used": ["claude-sonnet-5-5"]})
    assert driver.meta_is_set_aside({"host_error": HOST_ERROR_TEXT, "set_aside": True})
    assert not driver.meta_is_set_aside({"host_error": LIMIT_TEXT, "set_aside": False, "is_error": True, "models_used": []})
    assert not driver.meta_is_set_aside({"is_error": False, "models_used": []})


def _conversation(root, cid, meta):
    (root / cid).mkdir(parents=True)
    (root / cid / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return json.dumps({"id": cid, "fixture": meta.get("fixture")})


def test_the_sweep_sets_aside_a_host_error_moves_an_interrupted_one_and_leaves_an_answer(tmp_path, monkeypatch):
    root = tmp_path / "claude-code"
    monkeypatch.setattr(driver, "LEDGER", root)
    monkeypatch.setattr(driver, "INTERRUPTED", tmp_path / "local" / "interrupted")
    ledger = root / "ledger.jsonl"
    rows = [
        _conversation(root, "cc-smoke", {"fixture": "SMOKE", "is_error": True, "models_used": [], "capture_tool_calls": 0, "first_answer": True}),
        _conversation(root, "cc-F1-r1", {"fixture": "F1", "is_error": False, "models_used": ["claude-sonnet-5-5"]}),
    ]
    ledger.write_text("".join(r + "\n" for r in rows), encoding="utf-8")
    (root / "cc-F2-r1").mkdir()  # an interrupted conversation: no record
    (root / "cc-F2-r1" / "mcp.json").write_text("{}", encoding="utf-8")
    (root / "scores").mkdir()  # never a conversation
    assert driver.sweep(ledger) == [
        "INTERRUPTED-SET-ASIDE cc-F2-r1 moved to e1t/local/interrupted/cc-F2-r1-1 (no record was written; never scored or committed; 0 rows removed)",
        "HOST-ERROR-SET-ASIDE cc-smoke kept as e1t/ledger/claude-code/host-errors/cc-smoke-1; its ledger row removed (1 row)",
    ]
    assert (tmp_path / "local" / "interrupted" / "cc-F2-r1-1" / "mcp.json").is_file() and (root / "scores").is_dir()
    assert not (root / "cc-smoke").exists() and (root / "host-errors" / "cc-smoke-1" / "meta.json").is_file()
    assert [r["id"] for r in driver.ledger_rows(ledger)] == ["cc-F1-r1"] and (root / "cc-F1-r1").is_dir()
    assert driver.sweep(ledger) == []
    # a set-aside an interruption left half done (the row gone, the folder not yet moved), with a kept first attempt
    _conversation(root, "cc-smoke", {"fixture": "SMOKE", "host_error": HOST_ERROR_TEXT, "set_aside": True})
    _conversation(root, "cc-smoke.attempt1", {"fixture": "SMOKE"})
    assert driver.sweep(ledger) == ["HOST-ERROR-SET-ASIDE cc-smoke kept as e1t/ledger/claude-code/host-errors/cc-smoke-2; its ledger row removed (0 rows)"]
    assert sorted(p.name for p in (root / "host-errors").iterdir()) == ["cc-smoke-1", "cc-smoke-2", "cc-smoke-2.attempt1"]
    assert not (root / "cc-smoke.attempt1").exists()


def test_the_smoke_guard_reads_every_check_smoke_ok_prints_after(tmp_path, monkeypatch):
    root = tmp_path / "claude-code"
    monkeypatch.setattr(driver, "LEDGER", root)
    assert not driver.smoke_passed()
    good = {"is_error": False, "models_used": ["m"], "capture_initialized": True, "capture_surface_matches_key": True, "result_subtype": "success", "first_answer": True, "capture_tool_names": ["list_fact_categories"]}
    _conversation(root, "cc-smoke", good)
    assert driver.smoke_passed()
    for change in ({"capture_tool_names": []}, {"capture_surface_matches_key": False}, {"capture_initialized": False},
                   {"result_subtype": None, "first_answer": False}, {"host_error": "x", "set_aside": False}, {"set_aside": True, "host_error": "x"}):
        (root / "cc-smoke" / "meta.json").write_text(json.dumps(dict(good, **change)), encoding="utf-8")
        assert not driver.smoke_passed(), change


def _standin(tmp_path, monkeypatch):
    """A stand-in host on PATH: each call prints the next stream named in
    E1T_STANDIN_STREAMS and exits 1 when the stream ends with an error."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    host = bin_dir / "claude"
    host.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "if '--version' in sys.argv:\n"
        "    print(os.environ.get('E1T_STANDIN_VERSION', '2.1.311') + ' (Claude Code)')\n"
        "    sys.exit(0)\n"
        "state = os.environ['E1T_STANDIN_STATE']\n"
        "n = int(open(state).read()) if os.path.exists(state) else 0\n"
        "open(state, 'w').write(str(n + 1))\n"
        "lines = open(os.environ['E1T_STANDIN_STREAMS'].split(',')[n], encoding='utf-8').read().splitlines()\n"
        "version = os.environ.get('E1T_STANDIN_VERSION', '2.1.311')\n"
        "for ln in lines:\n"
        "    e = json.loads(ln)\n"
        "    if e.get('subtype') == 'init':\n"
        "        e['claude_code_version'] = version\n"
        "    print(json.dumps(e))\n"
        "sys.exit(1 if json.loads(lines[-1]).get('is_error') else 0)\n",
        encoding="utf-8",
    )
    host.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(driver, "wait_for_exit_lines", lambda *a, **k: True)  # the stand-in starts no server
    # the capture the real shim would write: an answered initialize, no tool call
    monkeypatch.setattr(driver, "read_capture", lambda d: [{"t": "t", "dir": "server", "line": json.dumps({"jsonrpc": "2.0", "id": 0, "result": {"instructions": "x"}})}])
    monkeypatch.setattr(driver, "surface_matches_key", lambda s: True)

    def calls(*streams):
        files = []
        for i, stream in enumerate(streams):
            f = tmp_path / f"stream-{len(list(tmp_path.glob('stream-*')))}-{i}.jsonl"
            f.write_text("".join(json.dumps(e) + "\n" for e in stream), encoding="utf-8")
            files.append(str(f))
        state = tmp_path / f"state-{len(list(tmp_path.glob('state-*')))}"
        monkeypatch.setenv("E1T_STANDIN_STATE", str(state))
        monkeypatch.setenv("E1T_STANDIN_STREAMS", ",".join(files))
    return calls


def test_a_batch_reads_each_host_error_by_the_key_s_rule(tmp_path, monkeypatch, capsys, pinned):
    """The whole batch path against a stand-in host: a host error before
    the model wrote is set aside with no row; one after the model began to
    answer, at either turn, is kept as it ran and never re-run; each stops
    the batch; the batch's later run skips what is recorded, re-runs the
    set-aside one from its first turn, and stops on a host version that
    differs from the batch's first recorded conversation."""
    root = tmp_path / "ledger" / "claude-code"
    monkeypatch.setattr(driver, "LEDGER", root)
    monkeypatch.setattr(driver, "INTERRUPTED", tmp_path / "local" / "interrupted")
    calls = _standin(tmp_path, monkeypatch)
    args = ["fixtures", "--model", "sonnet", "--repeats", "1", "--served", str(pinned)]
    calls(HOST_ERROR_STREAM)
    assert driver.main(["smoke", "--model", "sonnet", "--served", str(pinned)]) == 2
    out = capsys.readouterr().out
    assert "CONVERSATION" not in out and f"DRIVER-STOP cc-smoke: {key.HOST_ERROR_STOP} (turn 1: {HOST_ERROR_TEXT}); kept as e1t/ledger/claude-code/host-errors/cc-smoke-1, no ledger row" in out
    calls(AFTER_TOOL)  # the smoke is never scored: an error after a tool call sets it aside too
    assert driver.main(["smoke", "--model", "sonnet", "--served", str(pinned)]) == 2
    out = capsys.readouterr().out
    assert f"DRIVER-STOP cc-smoke: {key.HOST_ERROR_AFTER} (turn 1: {LIMIT_TEXT}); the smoke is never scored, so it is set aside; kept as e1t/ledger/claude-code/host-errors/cc-smoke-2, no ledger row" in out
    assert driver.main(args) == 2 and "DRIVER-STOP the smoke has not passed" in capsys.readouterr().out
    # a passing smoke, as the real one leaves it
    _conversation(root, "cc-smoke", {"fixture": "SMOKE", "capture_initialized": True, "capture_surface_matches_key": True, "result_subtype": "success", "first_answer": True, "capture_tool_names": ["list_fact_categories"]})
    calls(ASKS, TURN2_ERROR)  # F1: the model asks; the resumed second turn meets the host's error
    assert driver.main(args) == 2
    out = capsys.readouterr().out
    assert "CONVERSATION cc-F1-r1 fixture F1" in out and "second-turn True" in out
    assert f"DRIVER-STOP cc-F1-r1: {key.HOST_ERROR_AFTER} (turn 2: {LIMIT_TEXT}); kept as it ran, with its row, and never re-run" in out
    calls(AFTER_TOOL)  # F2: the host's error after the model called a tool
    assert driver.main(args) == 2
    out = capsys.readouterr().out
    assert "SKIP cc-F1-r1 already in the ledger" in out and f"DRIVER-STOP cc-F2-r1: {key.HOST_ERROR_AFTER} (turn 1: {LIMIT_TEXT})" in out
    calls(HOST_ERROR_STREAM)  # F3: the host's error before the model wrote anything
    assert driver.main(args) == 2
    out = capsys.readouterr().out
    assert "SKIP cc-F2-r1 already in the ledger" in out and f"DRIVER-STOP cc-F3-r1: {key.HOST_ERROR_STOP} (turn 1: {HOST_ERROR_TEXT}); kept as e1t/ledger/claude-code/host-errors/cc-F3-r1-1" in out
    calls(ANSWER)
    monkeypatch.setenv("E1T_STANDIN_VERSION", "2.1.312")  # the host updated itself between two runs of the batch
    assert driver.main(args) == 2
    out = capsys.readouterr().out
    assert "CONVERSATION cc-F3-r1 fixture F3" in out and "DRIVER-STOP cc-F3-r1: the host or the model changed inside the batch" in out
    assert [r["id"] for r in driver.ledger_rows(root / "ledger.jsonl")] == ["cc-F1-r1", "cc-F2-r1", "cc-F3-r1"]
    f1 = json.loads((root / "cc-F1-r1" / "meta.json").read_text(encoding="utf-8"))
    assert f1["host_error_turn"] == 2 and f1["set_aside"] is False and f1["first_answer"] is True and f1["second_turn_sent"] is True
    assert LIMIT_TEXT not in (root / "cc-F1-r1" / "visible.md").read_text(encoding="utf-8")
    f2 = json.loads((root / "cc-F2-r1" / "meta.json").read_text(encoding="utf-8"))
    assert f2["host_error_turn"] == 1 and f2["set_aside"] is False and f2["first_answer"] is False
    aside = json.loads((root / "host-errors" / "cc-F3-r1-1" / "meta.json").read_text(encoding="utf-8"))
    assert aside["set_aside"] is True and aside["host_error"] == HOST_ERROR_TEXT and aside["exit_codes"] == [1]
    assert driver.main(["status"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "HOST-ERRORS 3 set aside: cc-F3-r1-1 cc-smoke-1 cc-smoke-2"


def test_a_conversation_with_a_row_is_never_run_again_even_with_no_text(tmp_path, monkeypatch, capsys, pinned):
    """A model that only called tools until the turn cap has a row and no
    text: the batch's next run skips it, so it is never re-drawn and never
    gets a second row. So does a row written at a stop (the server did not
    start, or its surface was not the key's): those stops go to the
    Architect, never to a re-run."""
    root = tmp_path / "ledger" / "claude-code"
    monkeypatch.setattr(driver, "LEDGER", root)
    monkeypatch.setattr(driver, "INTERRUPTED", tmp_path / "local" / "interrupted")
    calls = _standin(tmp_path, monkeypatch)
    _conversation(root, "cc-smoke", {"fixture": "SMOKE", "capture_initialized": True, "capture_surface_matches_key": True, "result_subtype": "success", "first_answer": True, "capture_tool_names": ["list_fact_categories"]})
    capped = [_init(), _model([{"type": "tool_use", "id": "t1", "name": "mcp__metricmine-gold__query", "input": {}}]), _result(True, USED, "", "error_max_turns")]
    args = ["fixtures", "--model", "sonnet", "--repeats", "1", "--served", str(pinned)]
    calls(capped, ANSWER, HOST_ERROR_STREAM)  # F1 runs out of turns with no text; F2 answers; F3 meets the host's error
    assert driver.main(args) == 2
    out = capsys.readouterr().out
    assert "CONVERSATION cc-F1-r1 fixture F1" in out and "subtype error_max_turns" in out and "DRIVER-STOP cc-F3-r1" in out
    assert json.loads((root / "cc-F1-r1" / "meta.json").read_text(encoding="utf-8"))["first_answer"] is False
    calls(ANSWER)
    assert driver.main(args) == 0
    out = capsys.readouterr().out
    assert "SKIP cc-F1-r1 already in the ledger" in out and "SKIP cc-F2-r1 already in the ledger" in out and "BATCH-DONE fixtures" in out
    assert [r["id"] for r in driver.ledger_rows(root / "ledger.jsonl")] == ["cc-F1-r1", "cc-F2-r1", "cc-F3-r1"]
    assert not (root / "cc-F1-r1.attempt1").exists()
    good_capture, good_surface = driver.read_capture, driver.surface_matches_key
    for n, (broken, line) in enumerate((("read_capture", key.SERVER_DID_NOT_START), ("surface_matches_key", "the server's surface is not the key's"))):
        root = tmp_path / f"stop-{n}" / "claude-code"
        monkeypatch.setattr(driver, "LEDGER", root)
        _conversation(root, "cc-smoke", {"fixture": "SMOKE", "capture_initialized": True, "capture_surface_matches_key": True, "result_subtype": "success", "first_answer": True, "capture_tool_names": ["list_fact_categories"]})
        monkeypatch.setattr(driver, broken, (lambda d: []) if broken == "read_capture" else (lambda surface: False))
        calls(capped)
        assert driver.main(args) == 2
        assert f"DRIVER-STOP cc-F1-r1: {line}" in capsys.readouterr().out
        monkeypatch.setattr(driver, "read_capture", good_capture)
        monkeypatch.setattr(driver, "surface_matches_key", good_surface)
        calls(ANSWER, ANSWER)
        assert driver.main(args) == 0
        out = capsys.readouterr().out
        assert "SKIP cc-F1-r1 already in the ledger" in out and "CONVERSATION cc-F1-r1" not in out and "BATCH-DONE fixtures" in out
        assert [r["id"] for r in driver.ledger_rows(root / "ledger.jsonl")] == ["cc-F1-r1", "cc-F2-r1", "cc-F3-r1"]
        assert not (root / "cc-F1-r1.attempt1").exists()
