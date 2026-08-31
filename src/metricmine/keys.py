"""canonical_key v2 reference implementation (D-18; docs/spec/engine.md §3).

This module is the Python half of the dual-implementation keying rule: the
SQL half runs inside engine-emitted models as
``sha256(lower(to_json(<payload struct>)))`` over the canonical payload,
and the committed golden vectors (``tests/golden/canonical_key_v2.json``)
pin both halves to the same answers. Function-level semantics were probed
live at the pinned DuckDB engine (F-11); the requirements below are
verified behavior, never inference:

- **Payload keys** (record keys and derived degenerate identities): every
  value renders to canonical text (or JSON null), fields serialize as a
  compact JSON object sorted by lowercased field name (sortedness is an
  emission-time property; DuckDB's ``to_json`` does not sort), the entire
  serialization lowercases, then SHA-256 hex. Interior whitespace in
  values is PRESERVED on this path: ``CAST(TIMESTAMP AS VARCHAR)`` keeps
  its space and the SQL path never strips it.
- **Manifest keys** (schema keys): the field-name list serializes as a
  compact JSON array in DECLARED order (never sorted), lowercases, then
  SHA-256 hex.
- **Scalar keys** (the D-18 scalar path): canonical text, lowercased,
  ALL whitespace removed, hyphens preserved, then SHA-256 hex.

Canonical text rendering is scale- and platform-safe: decimals render via
``decimal.Decimal`` (``2.50`` stays ``"2.50"``), never float repr;
timestamps render ``YYYY-MM-DD HH:MM:SS``; booleans render ``true`` /
``false`` exactly as DuckDB casts them. Unsupported inputs raise instead
of guessing: a fail-closed reference implementation.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from decimal import Decimal
from typing import Mapping, Sequence

__all__ = [
    "render_value",
    "canonical_payload",
    "payload_key",
    "canonical_manifest",
    "manifest_key",
    "scalar_key",
]


def render_value(value: object) -> str | None:
    """Render one payload value to canonical text, or None for JSON null.

    Mirrors the emitted SQL's ``CAST(<col> AS VARCHAR)`` at the pinned
    engine (F-11): scale-preserving decimals, ``true``/``false`` booleans,
    ``YYYY-MM-DD HH:MM:SS`` timestamps. Floats are rejected outright;
    float repr is platform-hostile and the engine never passes one
    (docs/spec/engine.md §3.2).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        raise TypeError(
            "float payload values are not canonical; pass decimal.Decimal"
            " (docs/spec/engine.md §3.2)"
        )
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dt.datetime):
        if value.tzinfo is not None:
            raise TypeError(
                "timezone-aware datetimes are not canonical; the warehouse"
                " stores naive TIMESTAMP"
            )
        if value.microsecond:
            raise TypeError(
                "sub-second timestamps are unverified against the SQL path;"
                " canonical rendering is YYYY-MM-DD HH:MM:SS (F-11)"
            )
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError(f"no canonical rendering for {type(value).__name__}")


def canonical_payload(fields: Mapping[str, object]) -> str:
    """Serialize a payload to its canonical (pre-hash) form.

    Compact JSON object of canonical-text values (or null), fields sorted
    by lowercased name (Unicode codepoint order), the whole serialization
    lowercased. This is byte-for-byte what the SQL path feeds sha256():
    ``lower(to_json(<struct with pre-sorted, VARCHAR-cast members>))``.
    """
    lowered = [name.lower() for name in fields]
    if len(set(lowered)) != len(lowered):
        raise ValueError(
            "payload field names collide after lowercasing; keys are"
            " case-insensitive (D-18)"
        )
    rendered = {name: render_value(value) for name, value in fields.items()}
    ordered = dict(sorted(rendered.items(), key=lambda item: item[0].lower()))
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).lower()


def payload_key(fields: Mapping[str, object]) -> str:
    """Record key (or derived degenerate identity) over a payload."""
    return _sha256(canonical_payload(fields))


def canonical_manifest(names: Sequence[str]) -> str:
    """Serialize a schema manifest to its canonical (pre-hash) form.

    Compact JSON array of the field names in DECLARED order (manifests
    are order-sensitive by design, D-18) with the whole serialization
    lowercased.
    """
    if isinstance(names, str):
        raise TypeError("a manifest is a sequence of field names, not a string")
    return json.dumps(list(names), separators=(",", ":"), ensure_ascii=False).lower()


def manifest_key(names: Sequence[str]) -> str:
    """Schema key over a manifest (columns-dimension key)."""
    return _sha256(canonical_manifest(names))


def scalar_key(value: object) -> str:
    """D-18 scalar-path key: text, lowercase, whitespace out, hyphens kept."""
    rendered = render_value(value)
    if rendered is None:
        raise TypeError("the scalar path has no null rendering; got None")
    normalized = "".join(rendered.lower().split())
    return _sha256(normalized)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
