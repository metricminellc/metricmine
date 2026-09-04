"""Fetch the published demo artifact and verify it against the manifest.

Governing decisions: D-03 and D-33 as amended by Amendment S (Arc 6).

The demo artifact `demo/demo.duckdb` is a release asset, never committed.
The committed digest manifest `demo/demo.digest.json` names the release
it ships with and pins its sha256 and size; this script downloads that
asset keylessly from the GitHub release, verifies the bytes against the
manifest, then verifies the file's gold content against the manifest's
content section (the same D-33 claim CI proves on a fresh build). Path A
of the walkthrough (serve the artifact straight into Claude Desktop) runs
on this file; `make demo` builds the same content locally without it.

    uv run python scripts/fetch_demo.py        (make demo-fetch)

No key. Exit 0 on a verified artifact, 1 on any verification failure, 2
when the manifest names no published release yet (build it: make demo).
"""

from __future__ import annotations

import shutil
import sys
import urllib.error
import urllib.request

from metricmine.export_demo import (
    DEFAULT_DEST,
    DEFAULT_MANIFEST,
    compare_content,
    file_sha256,
    read_manifest,
)

REPOSITORY = "metricminellc/metricmine"
USER_AGENT = "metricmine-fetch-demo/0.1"


def asset_url(release: str, name: str) -> str:
    return f"https://github.com/{REPOSITORY}/releases/download/{release}/{name}"


def main() -> int:
    if not DEFAULT_MANIFEST.exists():
        print(f"digest manifest not found at {DEFAULT_MANIFEST}", file=sys.stderr)
        return 2
    manifest = read_manifest(DEFAULT_MANIFEST)
    artifact = manifest["artifact"]
    release = artifact.get("release")
    if not release:
        print(
            "this tree has no published demo artifact yet (the manifest names"
            " no release); build it locally: make demo"
        )
        return 2
    url = asset_url(release, artifact["name"])
    if DEFAULT_DEST.exists() and file_sha256(DEFAULT_DEST) == artifact["sha256"]:
        print(f"{DEFAULT_DEST} already matches the manifest (release {release})")
    else:
        print(f"downloading {url}")
        DEFAULT_DEST.parent.mkdir(parents=True, exist_ok=True)
        part = DEFAULT_DEST.with_name(DEFAULT_DEST.name + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=600) as resp, open(part, "wb") as out:
                shutil.copyfileobj(resp, out)
        except urllib.error.HTTPError as exc:
            part.unlink(missing_ok=True)
            print(
                f"ERROR: {url} answered HTTP {exc.code}; the release asset may"
                " not be published yet. Build it locally instead: make demo"
            )
            return 1
        digest = file_sha256(part)
        size = part.stat().st_size
        if (digest, size) != (artifact["sha256"], artifact["bytes"]):
            part.unlink(missing_ok=True)
            print(
                "ERROR: the downloaded asset does not match the manifest\n"
                f"  manifest sha256 {artifact['sha256']} bytes {artifact['bytes']}\n"
                f"  download sha256 {digest} bytes {size}\n"
                "Nothing kept. Build it locally instead: make demo"
            )
            return 1
        part.replace(DEFAULT_DEST)
        print(f"fetched {DEFAULT_DEST} ({size} bytes, sha256 {digest})")
    problems = compare_content(DEFAULT_DEST, manifest)
    if problems:
        for problem in problems:
            print(f"FAIL {problem}")
        return 1
    content = manifest["content"]
    print(
        f"verified: {len(content['tables'])} tables and {len(content['views'])}"
        f" views match the manifest (release {release})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
