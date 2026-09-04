"""Shared mechanics for the committed-extract fetch scripts (D-15 as amended).

Every source's fetch script is a thin, constants-only program in the
scripts/fetch_sample.py pattern: the publisher URL, the window, and the
budget are code, never arguments. This module carries what they share:

- ``download``: an atomic download into gitignored data/raw/ (a .part file
  until complete), with the project's User-Agent, skipped when the raw
  file already exists.
- ``verify_raw``: the raw download's sha256 against the value the script
  pins once a first run has measured it. Different bytes mean the publisher
  revised the artifact; the script prints the revision and refuses to
  extract, so a rerun is byte-identical while the artifact is unchanged
  and a revision is a loud finding, never a silent re-extract.
- ``write_extract``: the deterministic CSV writer (UTF-8, LF endings,
  rows sorted lexicographically by every column, a header row), the
  budget check, and the one-line receipt every script prints:
  ``OK <source>: <rows> rows, <bytes> bytes, extract sha256 <hex>``.
"""

from __future__ import annotations

import csv
import hashlib
import io
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "metricmine-fetch-sample/0.1"
RAW_ROOT = Path("data/raw")
SAMPLES_ROOT = Path("data/samples")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> Path:
    """Fetch ``url`` into ``dest`` once; an interrupted download leaves
    only the .part file, so the next run re-downloads cleanly."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return dest
    print(f"downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    part = dest.with_name(dest.name + ".part")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp, open(part, "wb") as out:
            shutil.copyfileobj(resp, out)
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"ERROR: {url} answered HTTP {exc.code}; the publisher may be"
            " down or may have moved the file. Nothing written."
        ) from exc
    part.replace(dest)
    return dest


def verify_raw(path: Path, pinned_sha256: str | None) -> str:
    """The raw artifact's digest, checked against the pinned value.

    ``pinned_sha256`` is None only before a first run has measured it; from
    then on the script carries the value and a mismatch is a refusal.
    """
    actual = sha256_path(path)
    if pinned_sha256 is None:
        print(f"raw {path.name}: sha256 {actual} (unpinned; copy it into RAW_SHA256 once reviewed)")
        return actual
    if actual != pinned_sha256:
        raise SystemExit(
            f"ERROR: the publisher artifact {path.name} has changed:\n"
            f"  pinned sha256 {pinned_sha256}\n"
            f"  actual sha256 {actual}\n"
            "The extract is NOT rewritten. Record the revision as a finding,"
            " re-window against the new bytes deliberately, and re-pin."
        )
    print(f"raw {path.name}: sha256 {actual} (matches the pinned value)")
    return actual


def write_extract(
    source: str,
    out_path: Path,
    header: list[str],
    rows: list[list[str]],
    max_bytes: int,
) -> str:
    """Write the deterministic CSV and print the receipt line.

    Rows are sorted lexicographically by every column so the file is a
    function of the window and nothing else; the budget is the D-15
    per-source cap the calling script declares.
    """
    rows = sorted(rows)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    data = buf.getvalue().encode("utf-8")
    if len(data) > max_bytes:
        raise SystemExit(
            f"ERROR: {source} extract is {len(data)} bytes, over the"
            f" {max_bytes}-byte budget; narrow the window in the script."
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"OK {source}: {len(rows)} rows, {len(data)} bytes, extract sha256 {digest}")
    return digest


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    """A committed extract (or any CSV) as header plus rows."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        return header, [row for row in reader]


def main_guard(fn) -> None:
    try:
        sys.exit(fn())
    except KeyboardInterrupt:
        sys.exit(130)
