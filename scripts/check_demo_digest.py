"""Prove the published demo artifact is what this tree's pipeline produces.

Governing decisions: D-33 and D-03, both as amended by Amendment S (Arc 6).

Compares the freshly built working warehouse against the committed digest
manifest `demo/demo.digest.json` at the CONTENT layer: the gold object
sets match, every gold table matches by row count, every gold view
matches by row count and ordered content digest (the D-33 invariant; the
typed views carry no run lineage or audit columns, so their digests are
stable across builds and machines), and the registry matches by row
count and ordered digest over its five deterministic columns. Cell-level
table equality is deliberately not asserted: context_registry.loaded_at
and the captured_at columns are build-time stamps, honest audit metadata
that differs between any two builds by design (F-39); export-time
equality of whole rows is export_demo.verify's job within one build. Byte sizes and the artifact's
own sha256 never enter (machine-dependent; the sha256 in the manifest
pins the ONE published asset for `make demo-fetch`, never a rebuild).

When `demo/demo.duckdb` is also present locally (fetched or exported), it
is checked against the manifest too, so a stale local artifact is named.

A gold content change that lands without its manifest refresh goes red
here, and a stranger's fetched artifact is proven to serve exactly what
the pipeline builds. Run after a green `dbt build`; CI runs it in
contract-gate after gate two. Locally:

    uv run python scripts/check_demo_digest.py

No key, no network. Exit 0 on a full match, 1 on any mismatch, 2 when an
input is missing.
"""

from __future__ import annotations

import sys

from metricmine.export_demo import (
    DEFAULT_DEST,
    DEFAULT_MANIFEST,
    compare_content,
    read_manifest,
    resolve_source_path,
)


def main() -> int:
    source = resolve_source_path()
    if not source.exists():
        print(
            f"working warehouse not found at {source}; run the build first "
            "(make ingest, then dbt build)",
            file=sys.stderr,
        )
        return 2
    if not DEFAULT_MANIFEST.exists():
        print(f"digest manifest not found at {DEFAULT_MANIFEST}", file=sys.stderr)
        return 2
    manifest = read_manifest(DEFAULT_MANIFEST)
    content = manifest["content"]
    problems = compare_content(source, manifest)
    if problems:
        for problem in problems:
            print(f"built warehouse: FAIL {problem}")
        print(f"demo manifest mismatch: {len(problems)} difference(s)")
        return 1
    print(
        f"built warehouse: {len(content['tables'])} tables and"
        f" {len(content['views'])} views match the manifest"
    )
    for view, entry in content["views"].items():
        print(f"  view {view}: {entry['rows']} rows, digest match ({entry['digest']})")
    registry = content.get("registry")
    if registry:
        print(f"  registry: {registry['rows']} rows, digest match ({registry['digest']})")
    # The local artifact is informational: absent from a fresh clone by
    # design, and a stale one is refreshed by export or fetch, never a gate.
    if not DEFAULT_DEST.exists():
        print("local artifact: absent (make demo-fetch or make demo restores it)")
    elif compare_content(DEFAULT_DEST, manifest):
        print("local artifact: STALE against the manifest (make export-demo or make demo-fetch)")
    else:
        print("local artifact: matches the manifest")
    print("demo manifest matches the built warehouse content: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
