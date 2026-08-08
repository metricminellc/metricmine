"""Ownership manifest: build, serialize, read, drift-check (D-09; rule 8).

Canonical JSON, deterministic content only — no timestamps, so
regeneration is byte-reproducible. The manifest maps each emitted
repo-relative path to sha256 over its fixed-point bytes and never lists
itself.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from metricmine.engine import ENGINE_VERSION

MANIFEST_NAME = "ownership-manifest.json"


def file_digest(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def build_manifest(
    files: dict[str, str], mapping: dict, star: dict, output_dir: str
) -> dict:
    """The manifest over an emitted set keyed by bare filename."""
    return {
        "engine_version": ENGINE_VERSION,
        "sources": {
            "mapping_contract": {
                "id": mapping["id"],
                "version": mapping["version"],
            },
            "gold_contract": {"id": star["id"], "version": star["version"]},
        },
        "files": {
            f"{output_dir}/{name}": file_digest(content)
            for name, content in files.items()
        },
    }


def serialize_manifest(manifest: dict) -> str:
    return (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )


def read_manifest(output_path: Path) -> dict | None:
    """The committed manifest, or None on the first regeneration."""
    manifest_path = output_path / MANIFEST_NAME
    if not manifest_path.is_file():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def drifted_files(repo_root: Path, manifest: dict | None) -> list[str]:
    """Baseline-listed files whose current bytes diverge (human-owned now).

    A diverged file marks itself human-owned (rule 8): the engine refuses
    to overwrite it and names it instead. A missing file is not drift —
    re-emitting it is the engine's job.
    """
    if manifest is None:
        return []
    drifted = []
    for rel_path, digest in manifest["files"].items():
        target = Path(repo_root) / rel_path
        if not target.is_file():
            continue
        current = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
        if current != digest:
            drifted.append(rel_path)
    return drifted
