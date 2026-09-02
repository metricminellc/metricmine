"""The DCO check: every pull request commit carries a well-formed sign-off.

Enforces the CONTRIBUTING.md sign-off rule (Developer Certificate of
Origin 1.1). The check reads the pull request's commit range and requires
each commit body to carry a well-formed trailer:

    Signed-off-by: Name <email>

Scope, by design:
- Pull request commits only. Main's history is never evaluated: squash
  merges compile their message from the pull request, and certification
  happened on the branch commits this check already gated.
- Merge commits are skipped (squash-only repository; a merge commit carries
  no authored change).
- Commits authored by the repository's own automation are exempt; the
  exempt identities arrive in DCO_EXEMPT_AUTHORS (comma-separated author
  emails) so the workflow file is the single visible list.
- The trailer must be well-formed; author-identity equality is not
  enforced. The certification is the trailer itself, and the repository's
  squash flow rewrites author emails on main anyway.

Usage:

    python3 scripts/check_dco.py --base <sha> --head <sha>

Stdlib only, no network, no key. Exit 0 when every commit passes, 1 when
any fails, 2 on usage or git errors.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

TRAILER = re.compile(r"^Signed-off-by: .+ <[^<>@\s]+@[^<>@\s]+>$", re.MULTILINE)
COMMIT_SEP = "\x1e"
FIELD_SEP = "\x00"


def pr_commits(base: str, head: str) -> list[tuple[str, str, str, str]]:
    """(sha, author name, author email, body) for each non-merge commit."""
    out = subprocess.run(
        [
            "git",
            "log",
            "--no-merges",
            # git expands %x00/%x1e to the separator bytes; argv cannot
            # carry them literally.
            "--format=%H%x00%an%x00%ae%x00%B%x1e",
            f"{base}..{head}",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    commits = []
    for chunk in out.split(COMMIT_SEP):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        sha, name, email, body = chunk.split(FIELD_SEP, 3)
        commits.append((sha, name, email, body))
    return commits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="base SHA (excluded)")
    parser.add_argument("--head", required=True, help="head SHA (included)")
    args = parser.parse_args()

    exempt = {
        e.strip()
        for e in os.environ.get("DCO_EXEMPT_AUTHORS", "").split(",")
        if e.strip()
    }

    try:
        commits = pr_commits(args.base, args.head)
    except subprocess.CalledProcessError as exc:
        print(f"git log failed: {exc.stderr.strip()}", file=sys.stderr)
        return 2

    if not commits:
        print("no commits in range; nothing to check")
        return 0

    failures = 0
    for sha, name, email, body in commits:
        subject = body.splitlines()[0] if body.splitlines() else ""
        if email in exempt:
            print(f"EXEMPT {sha[:9]} {name} <{email}> :: {subject}")
            continue
        if TRAILER.search(body):
            print(f"PASS   {sha[:9]} {name} :: {subject}")
        else:
            failures += 1
            print(f"FAIL   {sha[:9]} {name} :: {subject}")
            print(
                "       missing or malformed 'Signed-off-by: Name <email>' "
                "trailer; amend with `git commit --amend -s` (see "
                "CONTRIBUTING.md, Sign-off)"
            )
    checked = len(commits)
    print(f"checked {checked} commit(s): {failures} failing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
