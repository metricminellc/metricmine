"""CI-surface tests for the working-tree guard (.claude/hooks/working_tree_guard.py).

The guard is a Claude Code PreToolUse hook: JSON in on stdin, a decision
out on stdout. These tests run the script exactly the way Claude Code does
(a subprocess on the system python3, CLAUDE_PROJECT_DIR in the
environment) against a throwaway project root, so every case here is the
measurement the runbook quotes. Keyless, network-free, warehouse-free.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD = _REPO_ROOT / ".claude" / "hooks" / "working_tree_guard.py"
SETTINGS = _REPO_ROOT / ".claude" / "settings.json"


def run_guard(payload, root, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if root is not None:
        env["CLAUDE_PROJECT_DIR"] = str(root)
    if env_extra:
        env.update(env_extra)
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    if not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)["hookSpecificOutput"]


def call(tool, root, cwd=None, **tool_input):
    return {
        "session_id": "test",
        "cwd": str(cwd or root),
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
    }


@pytest.fixture
def root(tmp_path):
    project = tmp_path / "project"
    (project / "docs").mkdir(parents=True)
    (project / "docs" / "note.md").write_text("inside\n")
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere" / "secret.txt").write_text("outside\n")
    return project.resolve()


def assert_denied(out, fragment):
    assert out is not None, "expected a deny decision, got no decision"
    assert out["hookEventName"] == "PreToolUse"
    assert out["permissionDecision"] == "deny"
    assert fragment in out["permissionDecisionReason"]
    assert "working-tree guard" in out["permissionDecisionReason"]


# --- the Deviation 4 class: Bash over the home directory ---------------------


def test_bash_find_over_home_is_denied(root):
    home = os.path.realpath(os.path.expanduser("~"))
    out = run_guard(call("Bash", root, command="find ~ -name libduckdb.dylib"), root)
    assert_denied(out, home)


def test_bash_find_over_home_library_is_denied(root):
    out = run_guard(
        call("Bash", root, command='find ~/Library -name "*.dylib" 2>/dev/null'), root
    )
    assert_denied(out, os.path.join(os.path.realpath(os.path.expanduser("~")), "Library"))


def test_bash_dollar_home_is_denied(root):
    out = run_guard(call("Bash", root, command="ls $HOME/Music"), root)
    assert_denied(out, "Music")


def test_bash_absolute_path_outside_is_denied(root, tmp_path):
    target = tmp_path / "elsewhere" / "secret.txt"
    out = run_guard(call("Bash", root, command=f"cat {target}"), root)
    assert_denied(out, str(target.resolve()))


def test_bash_parent_climb_is_denied(root):
    out = run_guard(call("Bash", root, command="cat ../elsewhere/secret.txt"), root)
    assert_denied(out, "secret.txt")


def test_bash_tmp_write_is_denied(root):
    out = run_guard(call("Bash", root, command="echo x > /tmp/scratch.txt"), root)
    assert_denied(out, "scratch.txt")


def test_bash_quoted_path_with_spaces_is_denied(root, tmp_path):
    spaced = tmp_path / "My Docs"
    spaced.mkdir()
    out = run_guard(call("Bash", root, command=f'cat "{spaced}/a.txt"'), root)
    assert_denied(out, "My Docs")


def test_bash_unbalanced_quotes_still_checked(root, tmp_path):
    target = tmp_path / "elsewhere" / "secret.txt"
    out = run_guard(call("Bash", root, command=f"echo 'oops {target}"), root)
    assert_denied(out, "secret.txt")


# --- what a session legitimately runs passes with no decision ---------------


@pytest.mark.parametrize(
    "command",
    [
        'uv run pytest -m "not local" -q',
        "uv run ruff check .",
        "git status --short && git log --oneline -3",
        "make scan",
        "export SSL_CERT_FILE=/etc/ssl/cert.pem",
        "ls /opt/homebrew/Cellar/duckdb",
        "/usr/bin/env python3 --version",
        "uv run dbt build --project-dir transform --profiles-dir transform --target local 2>/dev/null",
        "git commit -m 'docs: a subject' -m 'why: the body cites D-14 and HEAD~1'",
        "gh pr checks 105 --watch",
    ],
)
def test_bash_in_tree_and_system_paths_pass(root, command):
    assert run_guard(call("Bash", root, command=command), root) is None


def test_bash_absolute_path_inside_root_passes(root):
    command = f"MM_WAREHOUSE_PATH={root}/warehouse/metricmine.duckdb uv run dbt build"
    assert run_guard(call("Bash", root, command=command), root) is None


def test_bash_cd_into_root_passes(root):
    assert run_guard(call("Bash", root, command=f"cd {root} && ls"), root) is None


def test_bash_parent_climb_that_stays_inside_passes(root):
    assert run_guard(call("Bash", root, cwd=root / "docs", command="cat ../docs/note.md"), root) is None


# --- prose that starts with a slash is not a path ----------------------------


def test_bash_slash_command_quoted_in_a_commit_message_passes(root):
    command = "git commit -m 'feat(claude): the review Skill' -m 'why: gives /contract-review a fixed report shape and a line in the /hooks menu'"
    assert run_guard(call("Bash", root, command=command), root) is None


def test_bash_existing_top_level_directory_is_still_a_path(root):
    out = run_guard(call("Bash", root, command="ls /tmp"), root)
    assert_denied(out, "/tmp")


def test_bash_unknown_multi_segment_path_is_still_a_path(root):
    out = run_guard(call("Bash", root, command="cat /no-such-dir/secret.txt"), root)
    assert_denied(out, "secret.txt")


# --- the file tools -----------------------------------------------------------


@pytest.mark.parametrize("tool,key", [("Read", "file_path"), ("Edit", "file_path"), ("Write", "file_path"), ("NotebookEdit", "notebook_path"), ("Glob", "path"), ("Grep", "path")])
def test_file_tool_outside_root_is_denied(root, tmp_path, tool, key):
    target = tmp_path / "elsewhere" / "secret.txt"
    out = run_guard(call(tool, root, **{key: str(target)}), root)
    assert_denied(out, str(target.resolve()))


@pytest.mark.parametrize("tool,key", [("Read", "file_path"), ("Edit", "file_path"), ("Write", "file_path"), ("Glob", "path"), ("Grep", "path")])
def test_file_tool_inside_root_passes(root, tool, key):
    assert run_guard(call(tool, root, **{key: str(root / "docs" / "note.md")}), root) is None
    assert run_guard(call(tool, root, **{key: "docs/note.md"}), root) is None


def test_read_of_home_dotfile_is_denied(root):
    out = run_guard(call("Read", root, file_path="~/.zshrc"), root)
    assert_denied(out, ".zshrc")


def test_glob_without_path_passes(root):
    assert run_guard(call("Glob", root, pattern="**/*.py"), root) is None


def test_symlink_out_of_tree_is_denied(root, tmp_path):
    link = root / "docs" / "escape"
    link.symlink_to(tmp_path / "elsewhere")
    out = run_guard(call("Read", root, file_path=str(link / "secret.txt")), root)
    assert_denied(out, "secret.txt")


def test_unrelated_tool_gets_no_decision(root):
    assert run_guard(call("WebFetch", root, url="https://example.com"), root) is None


# --- Claude Code's own auto-memory directory, file tools only -----------------


@pytest.fixture
def config_dir(tmp_path):
    config = tmp_path / "claude-config"
    memory = config / "projects" / "-tmp-project" / "memory"
    memory.mkdir(parents=True)
    (memory / "MEMORY.md").write_text("- a memory\n")
    (config / "settings.json").write_text("{}\n")
    (config / "projects" / "-tmp-project" / "session.jsonl").write_text("{}\n")
    return config.resolve()


@pytest.mark.parametrize("tool,key", [("Read", "file_path"), ("Write", "file_path"), ("Edit", "file_path"), ("Glob", "path"), ("Grep", "path")])
def test_file_tool_in_claude_memory_dir_passes(root, config_dir, tool, key):
    target = config_dir / "projects" / "-tmp-project" / "memory" / "MEMORY.md"
    env = {"CLAUDE_CONFIG_DIR": str(config_dir)}
    assert run_guard(call(tool, root, **{key: str(target)}), root, env_extra=env) is None


def test_file_tool_elsewhere_in_claude_config_is_denied(root, config_dir):
    env = {"CLAUDE_CONFIG_DIR": str(config_dir)}
    out = run_guard(call("Read", root, file_path=str(config_dir / "settings.json")), root, env_extra=env)
    assert_denied(out, "settings.json")
    out = run_guard(call("Read", root, file_path=str(config_dir / "projects" / "-tmp-project" / "session.jsonl")), root, env_extra=env)
    assert_denied(out, "session.jsonl")


def test_bash_over_claude_memory_dir_is_denied(root, config_dir):
    target = config_dir / "projects" / "-tmp-project" / "memory" / "MEMORY.md"
    env = {"CLAUDE_CONFIG_DIR": str(config_dir)}
    out = run_guard(call("Bash", root, command=f"cat {target}"), root, env_extra=env)
    assert_denied(out, "MEMORY.md")


# --- failure modes ask instead of failing open --------------------------------


def test_malformed_input_asks(root):
    out = run_guard("{not json", root)
    assert out["permissionDecision"] == "ask"
    assert "could not evaluate" in out["permissionDecisionReason"]


def test_missing_project_dir_asks(root):
    out = run_guard(call("Bash", root, command="ls ~"), None)
    assert out["permissionDecision"] == "ask"
    assert "CLAUDE_PROJECT_DIR" in out["permissionDecisionReason"]


# --- the committed settings wire the guard to the right events ----------------


def test_settings_register_the_guard():
    settings = json.loads(SETTINGS.read_text())
    (entry,) = settings["hooks"]["PreToolUse"]
    for tool in ("Bash", "Read", "Edit", "Write", "NotebookEdit", "Glob", "Grep"):
        assert tool in entry["matcher"].split("|")
    (hook,) = entry["hooks"]
    assert hook["type"] == "command"
    assert "working_tree_guard.py" in hook["command"]
    assert "${CLAUDE_PROJECT_DIR}" in hook["command"]


def test_settings_keep_plan_files_inside_the_tree():
    settings = json.loads(SETTINGS.read_text())
    assert settings["plansDirectory"] == ".claude/plans"
    ignored = (_REPO_ROOT / ".gitignore").read_text().splitlines()
    assert ".claude/plans/" in ignored


def test_guard_is_executable_and_standard_library_only():
    assert os.access(GUARD, os.X_OK)
    text = GUARD.read_text()
    assert text.startswith("#!/usr/bin/env python3\n")
    for module in ("json", "os", "re", "shlex", "sys"):
        assert f"import {module}\n" in text
