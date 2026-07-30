"""Canonical JSON serialization and content hash for profile artifacts.

Spec: docs/spec/profiler.md §3–§4. Canonical form: UTF-8, sorted keys,
2-space indent, ensure_ascii false, single trailing newline. content_hash
covers the canonical serialization of the dataset section only. It is an
artifact checksum, not a warehouse hash key; canonical_key v2 (CLAUDE.md
rule 13) governs warehouse keys and is untouched here.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_bytes(obj: Any) -> bytes:
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    return text.encode("utf-8") + b"\n"


def content_hash(dataset: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(dataset)).hexdigest()
