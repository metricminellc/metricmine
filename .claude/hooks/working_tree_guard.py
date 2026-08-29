#!/usr/bin/env python3
"""The working-tree guard: a PreToolUse hook for Claude Code.

CLAUDE.md (Conventions) says: never read or write paths outside the
repository working tree. This script makes that rule deterministic. Claude
Code runs it before every Bash, Read, Edit, Write, NotebookEdit, Glob, and
Grep call (the matcher lives in .claude/settings.json), hands it the call
as JSON on stdin, and reads the decision back on stdout. The guard resolves
every path it can see against the project root and denies the call when a
path resolves outside it, naming the path. When it sees no path, it prints
nothing and the normal permission flow applies.

What it checks. File tools: file_path, notebook_path, and path. Bash: each
token that starts with /, ~, $HOME, or ${HOME}, or climbs with .., after
splitting NAME=value and --flag=value forms. Symlinks resolve through
realpath, so a link out of the tree counts as out.

What it allows outside the root: directories that hold installed software
and devices, never a person's files (/dev, /usr, /bin, /sbin, /opt, /etc
and its macOS twin /private/etc, /Library, /System, /Applications, /nix,
/proc, /sys). The home directory, /tmp, /var, and everything else outside
the root are denied.

What it cannot see: a path a subprocess computes, a path built from an
environment variable other than HOME, or a path assembled by a script.
This is a guard, not a sandbox; the prose rule stays in force where the
guard cannot look. On malformed input or an internal error the guard asks
for a permission prompt instead of failing open or locking the session.

Runs on the system python3 with the standard library only (Python 3.9+).
"""

import json
import os
import re
import shlex
import sys

FILE_TOOLS = {
    "Read": ("file_path",),
    "Edit": ("file_path",),
    "MultiEdit": ("file_path",),
    "Write": ("file_path",),
    "NotebookEdit": ("notebook_path",),
    "Glob": ("path",),
    "Grep": ("path",),
}

SYSTEM_PREFIXES = (
    "/dev",
    "/usr",
    "/bin",
    "/sbin",
    "/opt",
    "/etc",
    "/private/etc",
    "/Library",
    "/System",
    "/Applications",
    "/nix",
    "/proc",
    "/sys",
)

ASSIGNMENT = re.compile(r"^(?:--?[A-Za-z][A-Za-z0-9_-]*|[A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def decision(kind, reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": kind,
            "permissionDecisionReason": reason,
        }
    }


def emit(payload):
    sys.stdout.write(json.dumps(payload))
    sys.stdout.write("\n")


def under(path, root):
    """True when path is root or lives below it (both already real paths)."""
    return path == root or path.startswith(root + os.sep)


def resolve(token, cwd):
    """Expand ~ and $HOME, then resolve relative to cwd through realpath."""
    expanded = token
    for prefix in ("${HOME}", "$HOME"):
        if expanded.startswith(prefix):
            expanded = os.path.expanduser("~") + expanded[len(prefix) :]
            break
    expanded = os.path.expanduser(expanded)
    if not os.path.isabs(expanded):
        expanded = os.path.join(cwd, expanded)
    return os.path.realpath(expanded)


def looks_like_path(token):
    return (
        token.startswith(("/", "~", "$HOME", "${HOME}", "../"))
        or token == ".."
        or "/../" in token
        or token.endswith("/..")
    )


def bash_candidates(command):
    """Every token of a Bash command that names a path the guard can see."""
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    out = []
    for token in tokens:
        for part in (token, ASSIGNMENT.match(token).group(1) if ASSIGNMENT.match(token) else None):
            if part and looks_like_path(part):
                out.append(part)
    return out


def outside(candidate, cwd, root):
    """The real path when candidate resolves outside the root, else None."""
    real = resolve(candidate, cwd)
    if under(real, root):
        return None
    if any(under(real, prefix) for prefix in SYSTEM_PREFIXES):
        return None
    return real


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            raise ValueError("hook input is not a JSON object")
        root_env = os.environ.get("CLAUDE_PROJECT_DIR")
        if not root_env:
            emit(decision("ask", "working-tree guard: CLAUDE_PROJECT_DIR is not set, so the project root is unknown; confirm this call by hand."))
            return
        root = os.path.realpath(root_env)
        cwd = os.path.realpath(data.get("cwd") or root)
        tool = data.get("tool_name", "")
        tool_input = data.get("tool_input") or {}
        candidates = []
        if tool == "Bash":
            candidates = bash_candidates(str(tool_input.get("command", "")))
        elif tool in FILE_TOOLS:
            for key in FILE_TOOLS[tool]:
                value = tool_input.get(key)
                if value:
                    candidates.append(str(value))
        for candidate in candidates:
            real = outside(candidate, cwd, root)
            if real is not None:
                emit(
                    decision(
                        "deny",
                        "working-tree guard: {tool} names {path}, which resolves outside the "
                        "project root {root}. CLAUDE.md Conventions: never read or write paths "
                        "outside the repository working tree. Stage the input inside the "
                        "repository, or use a path under it, and retry.".format(
                            tool=tool, path=real, root=root
                        ),
                    )
                )
                return
    except Exception as exc:  # the guard must never crash silently
        emit(decision("ask", "working-tree guard could not evaluate this call ({}); confirm it by hand.".format(exc)))


if __name__ == "__main__":
    main()
