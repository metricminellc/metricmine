"""The capture shim's pass-through, the capture file, the Desktop switch,
and its check, measured through the launch line Desktop uses. Needs the
pinned served file."""

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

from conftest import E1T, REPO

sys.path.insert(0, str(E1T))
import capture_slice  # noqa: E402
import desktop_switch  # noqa: E402
import key  # noqa: E402

SHIM = E1T / "capture_shim.py"
F1 = key.BY_ID["F1"]
F1_ARGS = {
    "field": F1.field, "kind": F1.kinds[0],
    "claim": "A flag that marks stock-adjustment lines is wanted.",
    "query": "select * from gold.mart_invoice_lines_typed where not is_cancellation and quantity < 0",
}


async def _walk(command: str, args: list[str], env: dict) -> dict:
    import mcp.types as T
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, get_default_environment, stdio_client

    full = dict(get_default_environment())
    full.update(env)
    params = StdioServerParameters(command=command, args=args, env=full, cwd=tempfile.gettempdir())
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w, client_info=T.Implementation(name="e1t-test", version="1")) as s:
            init = await s.initialize()
            tools = (await s.list_tools()).tools
            cats = await s.call_tool("list_fact_categories", {})
            pf = await s.call_tool("prepare_feedback", F1_ARGS)
            return {
                "instructions_sha": hashlib.sha256((init.instructions or "").encode()).hexdigest(),
                "tools": [(t.name, t.title) for t in tools],
                "cats": json.dumps(cats.structuredContent, sort_keys=True),
                "pf": json.dumps(pf.structuredContent, sort_keys=True),
            }


def walk(command, args, env):
    return asyncio.run(_walk(command, args, env))


def test_the_shim_passes_every_byte_through_and_captures_the_payloads(pinned, tmp_path):
    env = {"MM_SERVE_DB": str(pinned)}
    direct = walk(sys.executable, ["-m", "metricmine.server"], env)
    cap = tmp_path / "cap"
    via = walk(sys.executable, [str(SHIM)], dict(env, MM_E1T_CAPTURE=str(cap)))
    assert direct == via
    assert direct["instructions_sha"] == key.INSTRUCTIONS_SHA256 and len(direct["tools"]) == key.TOOL_COUNT
    files = sorted(cap.glob("capture-*.jsonl"))
    assert len(files) == 1
    lines = files[0].read_text(encoding="utf-8").splitlines()
    c = capture_slice.counts(lines)
    assert c["tools_call"] == 2 and c["tools"] == ["list_fact_categories", "prepare_feedback"]
    assert c["client_methods"]["initialize"] == 1
    results = [json.loads(json.loads(ln)["line"]) for ln in lines if json.loads(ln)["dir"] == "server"]
    texts = json.dumps(results)
    assert '"rows_matching": 90' in texts and "FEEDBACK" in texts
    assert lines[-1].endswith('"line": "server exited 0"}')


def test_the_switch_edits_one_entry_leaves_the_other_untouched_and_restores_byte_for_byte(tmp_path, monkeypatch, pinned):
    config = tmp_path / "claude_desktop_config.json"
    original = {"mcpServers": {"other-server": {"command": "/x/y", "args": ["--token", "SECRET"], "env": {"OTHER_KEY": "value"}}, "metricmine-gold": {"command": "/old/python", "args": ["-m", "metricmine.server"], "env": {}}}, "theme": "dark"}
    config.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")
    before = config.read_bytes()
    monkeypatch.setattr(desktop_switch, "BACKUP", tmp_path / "backup.json")
    assert desktop_switch.main(["set", "--worktree", str(REPO), "--served", str(pinned), "--config", str(config)]) == 1  # no backup yet
    assert desktop_switch.main(["backup", "--config", str(config)]) == 0
    assert desktop_switch.main(["backup", "--config", str(config)]) == 0  # never overwritten
    assert desktop_switch.main(["set", "--worktree", str(REPO), "--served", str(pinned), "--config", str(config)]) == 0
    after = json.loads(config.read_text(encoding="utf-8"))
    assert after["mcpServers"]["other-server"] == original["mcpServers"]["other-server"]
    assert after["theme"] == "dark"
    entry = after["mcpServers"]["metricmine-gold"]
    assert entry["command"].endswith("/.venv/bin/python") and entry["args"] == [str(REPO / "e1t" / "capture_shim.py")]
    assert entry["env"]["MM_SERVE_DB"] == str(pinned) and entry["env"]["MM_E1T_CAPTURE"] == str(REPO / "e1t" / "capture")
    assert desktop_switch.main(["restore", "--config", str(config)]) == 0
    assert config.read_bytes() == before


def test_the_check_spawns_the_configured_line_and_measures_against_the_key(tmp_path, monkeypatch, pinned, capsys):
    config = tmp_path / "claude_desktop_config.json"
    config.write_text(json.dumps({"mcpServers": {"metricmine-gold": {"command": "/old", "args": [], "env": {}}}}) + "\n", encoding="utf-8")
    monkeypatch.setattr(desktop_switch, "BACKUP", tmp_path / "backup.json")
    desktop_switch.main(["backup", "--config", str(config)])
    desktop_switch.main(["set", "--worktree", str(REPO), "--served", str(pinned), "--config", str(config)])
    # the entry names the worktree's venv; this clone's venv is the interpreter under test
    data = json.loads(config.read_text())
    data["mcpServers"]["metricmine-gold"]["command"] = sys.executable
    data["mcpServers"]["metricmine-gold"]["env"]["MM_E1T_CAPTURE"] = str(tmp_path / "cap")
    config.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    capsys.readouterr()
    assert desktop_switch.main(["check", "--config", str(config)]) == 0
    out = capsys.readouterr().out
    assert f"instructions sha256 {key.INSTRUCTIONS_SHA256} ({key.INSTRUCTIONS_LENGTH} characters) MATCH" in out
    assert f"served sha256 {key.SERVED_SHA256} MATCH" in out
    assert f"tools {key.TOOL_COUNT}" in out and "prepare_feedback MATCH" in out and out.strip().endswith("CHECK-OK")


def test_slice_begin_and_end_around_a_live_shim(pinned, tmp_path, monkeypatch):
    cap = tmp_path / "cap"
    env = dict(os.environ, MM_SERVE_DB=str(pinned), MM_E1T_CAPTURE=str(cap))
    proc = subprocess.Popen([sys.executable, str(SHIM)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env, cwd=tempfile.gettempdir())
    try:
        init = json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}}) + "\n"
        proc.stdin.write(init.encode())
        proc.stdin.flush()
        proc.stdout.readline()
        proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n')
        proc.stdin.flush()
        time.sleep(0.5)
        monkeypatch.setenv("MM_E1T_CAPTURE", str(cap))
        monkeypatch.setattr(capture_slice, "MARK", tmp_path / "MARK.json")
        monkeypatch.setattr(capture_slice, "live_shim_pids", lambda: [proc.pid])
        assert capture_slice.main(["begin"]) == 0
        call = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_fact_categories", "arguments": {}}}) + "\n"
        proc.stdin.write(call.encode())
        proc.stdin.flush()
        proc.stdout.readline()
        dest = tmp_path / "t"
        assert capture_slice.main(["end", str(dest)]) == 0
        c = capture_slice.counts((dest / "capture.jsonl").read_text().splitlines())
        assert c["tools_call"] == 1 and c["client_methods"] == {"tools/call": 1} and c["server_results"] == 1
        monkeypatch.setattr(capture_slice, "live_shim_pids", lambda: [])
        assert capture_slice.main(["begin"]) == 1
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)
