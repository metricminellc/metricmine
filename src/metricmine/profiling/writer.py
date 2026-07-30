"""Write-if-changed artifact writer (spec §4 rule 6, §6).

Artifacts are immutable and monotonically numbered under
profiles/<schema>.<table>/vNNNN.json. Comparison is over whole-artifact
bytes, never content_hash alone, so a caps or schema_version change mints
a new version even when the dataset bytes are unchanged. The
vNNNN.meta.json sidecar carries run metadata and is exempt from the
determinism guarantee.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_VERSION_RE = re.compile(r"^v(\d{4})\.json$")


def latest_version(profile_dir: Path) -> int:
    versions = [
        int(m.group(1))
        for p in profile_dir.glob("v*.json")
        if (m := _VERSION_RE.match(p.name))
    ]
    return max(versions, default=0)


def write_if_changed(
    profile_dir: Path, artifact_bytes: bytes, meta: dict
) -> Path | None:
    """Write the next vNNNN artifact, or nothing when bytes are unchanged."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    current = latest_version(profile_dir)
    if current:
        newest = profile_dir / f"v{current:04d}.json"
        if newest.read_bytes() == artifact_bytes:
            return None
    minted = current + 1
    path = profile_dir / f"v{minted:04d}.json"
    path.write_bytes(artifact_bytes)
    sidecar = profile_dir / f"v{minted:04d}.meta.json"
    sidecar.write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path
