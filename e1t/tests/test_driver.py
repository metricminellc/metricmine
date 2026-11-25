"""The driver's pure parts: the plan, the command line, the stream reader,
the capture reader, and the scrubber. Nothing here runs the host."""

import json
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
