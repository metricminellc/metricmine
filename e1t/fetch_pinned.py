"""Fetch the pinned served file for E1T: the v1.3.0 release asset.

    uv run python e1t/fetch_pinned.py [--dest e1t/served/demo-v1.3.0.duckdb]

The experiment serves the v1.3.0 release asset, pinned by its sha256 and
never by its tag (the host plan, Section 3.6; measured November 2, 2026).
The file is downloaded keylessly from the release, verified by sha256 and
size, and kept under e1t/served/ (gitignored). The same bytes that
`make demo-fetch` places at demo/demo.duckdb may be given as --source. A file already present at the right
sha256 is kept. A mismatch keeps nothing and prints PINNED-MISMATCH.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from key import SERVED_BYTES as BYTES  # noqa: E402
from key import SERVED_RELEASE as RELEASE  # noqa: E402
from key import SERVED_SHA256 as SHA256  # noqa: E402

NAME = "demo.duckdb"
URL = f"https://github.com/metricminellc/metricmine/releases/download/{RELEASE}/{NAME}"
DEFAULT_DEST = HERE / "served" / f"demo-{RELEASE}.duckdb"


def rel(path: Path) -> str:
    """A path as the worktree prints it, the same on every machine."""
    try:
        return path.resolve().relative_to(HERE.parent.resolve()).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=str(DEFAULT_DEST))
    ap.add_argument("--source", default="", help="a local copy to verify and place instead of downloading")
    a = ap.parse_args(argv)
    dest = Path(a.dest)
    if dest.is_file() and sha256_file(dest) == SHA256 and dest.stat().st_size == BYTES:
        print(f"PINNED-OK {rel(dest)} already matches ({BYTES} bytes, sha256 {SHA256})")
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    if a.source:
        shutil.copyfile(a.source, part)
    else:
        from metricmine.tls import ssl_context

        req = urllib.request.Request(URL, headers={"User-Agent": "metricmine-e1t-fetch/1"})
        with urllib.request.urlopen(req, timeout=600, context=ssl_context()) as resp, open(part, "wb") as out:
            shutil.copyfileobj(resp, out)
    digest, size = sha256_file(part), part.stat().st_size
    if (digest, size) != (SHA256, BYTES):
        part.unlink(missing_ok=True)
        print(f"PINNED-MISMATCH got {size} bytes sha256 {digest}; expected {BYTES} bytes sha256 {SHA256}; nothing kept")
        return 1
    part.replace(dest)
    print(f"PINNED-OK {rel(dest)} fetched ({BYTES} bytes, sha256 {SHA256})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
