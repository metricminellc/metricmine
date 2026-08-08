"""Prep-session generator for tests/golden/canonical_key_v2.json.

Builds the golden vector set for canonical_key v2, computing canonical
serializations and keys via the reference implementation, then the
companion probe (probe_sql_parity.py) independently recomputes every
payload and manifest vector through DuckDB SQL at the pinned engine and
fails on any disagreement. Vectors ship only after both implementations
agree byte for byte.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "metricmine" / "src"))

from metricmine.keys import (  # noqa: E402
    canonical_manifest,
    canonical_payload,
    manifest_key,
    payload_key,
    render_value,
    scalar_key,
)

TS = dt.datetime(2009, 12, 1, 7, 45, 0)


def tv(value):
    """Encode a typed value for the JSON vector file."""
    if value is None:
        return {"t": "null"}
    if isinstance(value, bool):
        return {"t": "bool", "v": value}
    if isinstance(value, int):
        return {"t": "int", "v": value}
    if isinstance(value, Decimal):
        return {"t": "decimal", "v": str(value)}
    if isinstance(value, dt.datetime):
        return {"t": "timestamp", "v": value.strftime("%Y-%m-%d %H:%M:%S")}
    if isinstance(value, dt.date):
        return {"t": "date", "v": value.isoformat()}
    if isinstance(value, str):
        return {"t": "str", "v": value}
    raise TypeError(type(value))


PAYLOADS = [
    ("basic_two_fields", "Two plain string fields.",
     {"invoice_id": "489434", "stock_code": "85048"}, None),
    ("field_order_insensitive",
     "Same fields declared in reverse order produce the same key: payload"
     " keys sort by lowercased field name at serialization (emission-time"
     " property; to_json does not sort).",
     {"stock_code": "85048", "invoice_id": "489434"},
     {"invoice_id": "489434", "stock_code": "85048"}),
    ("case_insensitive_names_and_values",
     "Mixed-case field names and values lowercase into the same key.",
     {"Invoice_ID": "C489449", "Stock_Code": "22087"},
     {"invoice_id": "c489449", "stock_code": "22087"}),
    ("unicode_values",
     "Unicode lowercase parity (a-umlaut, sharp-s, u-umlaut) between"
     " Python str.lower() and DuckDB lower(), vector-verified (F-11).",
     {"note": "Über-Größe Ärmel"}, None),
    ("interior_whitespace_preserved",
     "Payload-path values keep interior whitespace; only the scalar path"
     " strips it (D-18).",
     {"description": "WHITE HANGING HEART T-LIGHT HOLDER"}, None),
    ("hyphen_preserved",
     "Hyphens survive canonicalization on every path (D-18 delta from"
     " 2023).",
     {"code": "ABC-123-x"}, None),
    ("decimal_scale_preserved",
     "DECIMAL(10,2) renders scale-preserving text: 2.50 never collapses"
     " to 2.5 (F-11).",
     {"unit_price": Decimal("2.50")}, None),
    ("decimal_integral_scale",
     "Integral decimals keep declared scale: 5.00 stays 5.00.",
     {"unit_price": Decimal("5.00")}, None),
    ("timestamp_render",
     "TIMESTAMP renders YYYY-MM-DD HH:MM:SS; the interior space survives"
     " the payload path (F-11).",
     {"invoiced_at": TS}, None),
    ("null_included_as_null",
     "A declared field whose value is NULL appears as JSON null —"
     " include-as-null, decided at the engine spec (§3.3).",
     {"customer_id": None, "invoice_id": "489434"}, None),
    ("boolean_render",
     "Booleans render true/false exactly as DuckDB casts them.",
     {"is_cancellation": True, "invoice_id": "C489449"}, None),
    ("negative_integer",
     "Negative integers render with the sign; cancellation quantities are"
     " the live case.",
     {"quantity": -1395}, None),
    ("empty_string_value",
     "Empty-string value round-trips; the empty-string digest was"
     " byte-verified against hashlib at the probe (F-11).",
     {"note": ""}, None),
    ("quote_escape_parity",
     "Embedded double quotes escape identically in Python json.dumps and"
     " DuckDB to_json.",
     {"note": 'says "hello"'}, None),
    ("line_identity_regular",
     "The form-(b) derived degenerate identity over the declared silver"
     " grain tuple (invoice_id, stock_code, quantity, unit_price) — a"
     " regular sales line.",
     {"invoice_id": "489434", "stock_code": "85048",
      "quantity": 12, "unit_price": Decimal("6.95")}, None),
    ("line_identity_cancellation",
     "The form-(b) derived identity for a cancellation line: C-prefixed"
     " invoice, negative quantity.",
     {"invoice_id": "C489449", "stock_code": "22087",
      "quantity": -12, "unit_price": Decimal("2.55")}, None),
]

MANIFESTS = [
    ("dim_manifest_v1",
     "The mapping contract v1.0.0 dimension-payload manifest in declared"
     " order: five dimension-role fields plus the derived line_identity.",
     ["invoice_id", "is_cancellation", "stock_code", "product_description",
      "customer_id", "line_identity"], None),
    ("dim_manifest_v1_reversed",
     "The same names reversed: manifests are ORDER-SENSITIVE by design"
     " (declared order, never sorted) — this key must differ from"
     " dim_manifest_v1.",
     ["line_identity", "customer_id", "product_description", "stock_code",
      "is_cancellation", "invoice_id"], None),
    ("measure_manifest_v1",
     "The mapping contract v1.0.0 measure manifest in declared order.",
     ["quantity", "unit_price"], None),
    ("manifest_case_insensitive",
     "Mixed-case names lowercase into the same manifest key.",
     ["Invoice_ID", "Stock_Code"], ["invoice_id", "stock_code"]),
    ("manifest_hyphen_preserved",
     "Hyphens survive in manifest names.",
     ["ab-cd"], None),
]

SCALARS = [
    ("scalar_empty_string",
     "sha256 of the empty string — the digest byte-verified against"
     " Python hashlib at the live probe (F-11).",
     ""),
    ("scalar_whitespace_stripped",
     "The scalar path removes ALL whitespace (spaces, tabs) after"
     " lowercasing.",
     "  Wh ite\tSpace  "),
    ("scalar_hyphen_preserved",
     "Hyphens preserved on the scalar path (D-18 delta from 2023).",
     "AB-C"),
    ("scalar_decimal_scale",
     "Scalar decimals render scale-preserving before hashing.",
     Decimal("2.50")),
]


def main() -> int:
    payload_out = []
    for name, desc, fields, alt in PAYLOADS:
        entry = {
            "name": name,
            "description": desc,
            "fields": {k: tv(v) for k, v in fields.items()},
            "canonical": canonical_payload(fields),
            "key": payload_key(fields),
        }
        if alt is not None:
            assert payload_key(alt) == entry["key"], name
            entry["fields_alt"] = {k: tv(v) for k, v in alt.items()}
        payload_out.append(entry)

    manifest_out = []
    for name, desc, names, alt in MANIFESTS:
        entry = {
            "name": name,
            "description": desc,
            "names": list(names),
            "canonical": canonical_manifest(names),
            "key": manifest_key(names),
        }
        if alt is not None:
            assert manifest_key(alt) == entry["key"], name
            entry["names_alt"] = list(alt)
        manifest_out.append(entry)

    by_name = {m["name"]: m for m in manifest_out}
    assert (by_name["dim_manifest_v1"]["key"]
            != by_name["dim_manifest_v1_reversed"]["key"])

    scalar_out = []
    for name, desc, value in SCALARS:
        rendered = render_value(value)
        normalized = "".join(rendered.lower().split())
        entry = {
            "name": name,
            "description": desc,
            "value": tv(value),
            "normalized": normalized,
            "key": scalar_key(value),
        }
        scalar_out.append(entry)

    empty = next(s for s in scalar_out if s["name"] == "scalar_empty_string")
    assert empty["key"] == hashlib.sha256(b"").hexdigest()

    doc = {
        "_comment": (
            "Golden vectors for canonical_key v2 (D-18; docs/spec/engine.md"
            " §3). Pinned answers for the dual-implementation rule: the"
            " Python reference (src/metricmine/keys.py) is held to these in"
            " CI (tests/test_canonical_key.py); the SQL path"
            " (sha256(lower(to_json(...)))) is held to the payload and"
            " manifest vectors by the consistency test that lands with the"
            " engine. Generated at the Sitting H prep session; every payload"
            " and manifest vector was cross-verified against DuckDB 1.4.3"
            " SQL before committing. canonical/normalized fields are the"
            " pre-hash serializations, kept legible for review and debugging."
        ),
        "payload": payload_out,
        "manifest": manifest_out,
        "scalar": scalar_out,
    }
    out = (Path(__file__).resolve().parents[1] / "metricmine" / "tests"
           / "golden" / "canonical_key_v2.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {out}: {len(payload_out)} payload, {len(manifest_out)}"
          f" manifest, {len(scalar_out)} scalar vectors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
