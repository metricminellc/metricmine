"""CI-surface tests holding canonical_key v2 to its golden vectors.

The Python half of the dual-implementation keying rule (D-18;
docs/spec/engine.md §3): src/metricmine/keys.py must reproduce every
pinned canonical serialization and key in tests/golden/canonical_key_v2.json.
The vectors were cross-verified against DuckDB SQL at the pinned engine
(1.4.3) at the Sitting H prep session; the committed SQL-vs-Python
consistency test lands with the engine per the ladder, reusing this same
golden file as its fixture.
"""

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

import pytest

from metricmine.keys import (
    canonical_manifest,
    canonical_payload,
    manifest_key,
    payload_key,
    render_value,
    scalar_key,
)

_GOLDEN = Path(__file__).resolve().parent / "golden" / "canonical_key_v2.json"
GOLDEN = json.loads(_GOLDEN.read_text(encoding="utf-8"))


def decode(typed: dict):
    t = typed["t"]
    if t == "null":
        return None
    v = typed["v"]
    if t == "str":
        return v
    if t == "int":
        return v
    if t == "decimal":
        return Decimal(v)
    if t == "timestamp":
        return dt.datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
    if t == "date":
        return dt.date.fromisoformat(v)
    if t == "bool":
        return v
    raise ValueError(t)


def decode_fields(fields: dict) -> dict:
    return {name: decode(typed) for name, typed in fields.items()}


@pytest.mark.parametrize(
    "vec", GOLDEN["payload"], ids=[v["name"] for v in GOLDEN["payload"]]
)
def test_payload_vectors(vec):
    fields = decode_fields(vec["fields"])
    assert canonical_payload(fields) == vec["canonical"]
    assert payload_key(fields) == vec["key"]
    if "fields_alt" in vec:
        alt = decode_fields(vec["fields_alt"])
        assert payload_key(alt) == vec["key"]


@pytest.mark.parametrize(
    "vec", GOLDEN["manifest"], ids=[v["name"] for v in GOLDEN["manifest"]]
)
def test_manifest_vectors(vec):
    assert canonical_manifest(vec["names"]) == vec["canonical"]
    assert manifest_key(vec["names"]) == vec["key"]
    if "names_alt" in vec:
        assert manifest_key(vec["names_alt"]) == vec["key"]


@pytest.mark.parametrize(
    "vec", GOLDEN["scalar"], ids=[v["name"] for v in GOLDEN["scalar"]]
)
def test_scalar_vectors(vec):
    assert scalar_key(decode(vec["value"])) == vec["key"]


def test_manifests_are_order_sensitive():
    by_name = {v["name"]: v for v in GOLDEN["manifest"]}
    assert (
        by_name["dim_manifest_v1"]["key"]
        != by_name["dim_manifest_v1_reversed"]["key"]
    ), "manifest keys must depend on declared order (D-18)"


def test_payload_keys_are_order_insensitive():
    a = {"x": "1", "y": "2"}
    b = {"y": "2", "x": "1"}
    assert payload_key(a) == payload_key(b)


def test_float_rejected():
    with pytest.raises(TypeError, match="decimal.Decimal"):
        render_value(2.5)


def test_subsecond_timestamp_rejected():
    with pytest.raises(TypeError, match="unverified"):
        render_value(dt.datetime(2009, 12, 1, 7, 45, 0, 123456))


def test_timezone_aware_timestamp_rejected():
    with pytest.raises(TypeError, match="naive"):
        render_value(dt.datetime(2009, 12, 1, 7, 45, tzinfo=dt.timezone.utc))


def test_lowercase_field_collision_rejected():
    with pytest.raises(ValueError, match="collide"):
        canonical_payload({"Amount": "1", "amount": "2"})


def test_scalar_null_rejected():
    with pytest.raises(TypeError, match="no null rendering"):
        scalar_key(None)


def test_manifest_string_rejected():
    with pytest.raises(TypeError, match="sequence"):
        canonical_manifest("invoice_id")
