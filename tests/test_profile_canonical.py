"""CI-surface tests for canonical serialization, caps, and versioning.

Warehouse-free and network-free: pure functions from metricmine.profiling
plus the write-if-changed writer against tmp_path. Pins the determinism
rules of docs/spec/profiler.md §4, the caps of §5, and the whole-artifact
versioning of §6.
"""

import re

from metricmine.profiling.build import (
    MAX_SAMPLE_VALUES,
    MAX_STRING_CHARS,
    TRUNCATION_SUFFIX,
    build_column_entry,
    build_profile,
)
from metricmine.profiling.canonical import canonical_bytes, content_hash
from metricmine.profiling.writer import write_if_changed
from metricmine.warehouse.base import ColumnStats


def _entry(**overrides):
    """A columns[] entry with sane defaults, overridable per test."""
    args = {
        "name": "c",
        "physical_type": "VARCHAR",
        "stats": ColumnStats(null_count=0, distinct_count=99, min=None, max=None),
        "values": ["a", "b", "c"],
        "row_count": 100,
    }
    args.update(overrides)
    return build_column_entry(**args)


def test_canonical_bytes_stable_and_key_order_insensitive():
    first = {"b": 1, "a": [1, 2], "nested": {"y": 2, "x": 1}}
    second = {"nested": {"x": 1, "y": 2}, "a": [1, 2], "b": 1}
    assert canonical_bytes(first) == canonical_bytes(second)
    assert canonical_bytes(first) == canonical_bytes(first)
    assert canonical_bytes(first).endswith(b"\n")
    assert not canonical_bytes(first).endswith(b"\n\n")


def test_canonical_bytes_utf8_not_escaped():
    assert "é".encode() in canonical_bytes({"s": "é"})


def test_content_hash_format_stability_sensitivity():
    digest = content_hash({"x": 1})
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
    assert digest == content_hash({"x": 1})
    assert digest != content_hash({"x": 2})


def test_float_rounding_to_six_places():
    stats = ColumnStats(null_count=1, distinct_count=30, min=0.123456789, max=9.87654321)
    entry = _entry(physical_type="DOUBLE", stats=stats, values=[0.111111119], row_count=3)
    assert entry["null_rate"] == 0.333333
    assert entry["min"] == 0.123457
    assert entry["max"] == 9.876543
    assert entry["sample_values"] == [0.111111]


def test_sample_values_capped_at_ten_ascending():
    values = [f"v{i:02d}" for i in range(15)]
    entry = _entry(stats=ColumnStats(0, 50, None, None), values=values)
    assert entry["sample_values"] == sorted(values)[:MAX_SAMPLE_VALUES]
    assert "distinct_values" not in entry


def test_distinct_values_iff_under_cap_and_samples_omitted():
    under = _entry(stats=ColumnStats(0, 3, None, None), values=["x", "y", "z"])
    assert under["distinct_values"] == ["x", "y", "z"]
    assert "sample_values" not in under

    over = _entry(stats=ColumnStats(0, 21, None, None), values=["x", "y", "z"])
    assert "distinct_values" not in over
    assert "sample_values" in over


def test_truncation_after_distinctness_distinct_count_authoritative():
    base = "x" * MAX_STRING_CHARS
    entry = _entry(
        stats=ColumnStats(0, 2, None, None), values=[base + "AAA", base + "BBB"]
    )
    truncated = base + TRUNCATION_SUFFIX
    # The two values collapse to the same emitted string; distinct_count
    # from the engine stays authoritative.
    assert entry["distinct_values"] == [truncated, truncated]
    assert entry["distinct_count"] == 2


def test_string_ordering_is_unicode_codepoint():
    # Codepoints: A=65, Z=90, b=98, é=233. No casefold, no locale collation.
    entry = _entry(stats=ColumnStats(0, 4, None, None), values=["b", "A", "é", "Z"])
    assert entry["distinct_values"] == ["A", "Z", "b", "é"]


def test_min_max_only_for_numeric_and_temporal():
    varchar = _entry(stats=ColumnStats(0, 30, "a", "z"), values=["a"])
    assert "min" not in varchar and "max" not in varchar
    numeric = _entry(
        physical_type="DECIMAL(38,9)", stats=ColumnStats(0, 30, 1, 9), values=[1]
    )
    assert numeric["min"] == 1 and numeric["max"] == 9


def _artifact(caps_override=None):
    entry = _entry(stats=ColumnStats(0, 2, None, None), values=["x", "y"])
    artifact = build_profile("bronze", "t", 100, 5, [entry])
    if caps_override:
        artifact = {**artifact, "caps": {**artifact["caps"], **caps_override}}
    return artifact


def test_write_if_changed_whole_artifact_bytes(tmp_path):
    first = canonical_bytes(_artifact())
    written = write_if_changed(tmp_path, first, {"run": 1})
    assert written is not None and written.name == "v0001.json"
    assert (tmp_path / "v0001.meta.json").is_file()

    # Identical bytes: nothing written, rerun leaves the directory as-is.
    assert write_if_changed(tmp_path, first, {"run": 2}) is None
    assert sorted(p.name for p in tmp_path.glob("v*.json")) == [
        "v0001.json",
        "v0001.meta.json",
    ]

    # A caps-only change leaves dataset and content_hash untouched but must
    # still mint the next version: comparison is whole-artifact bytes.
    changed = _artifact(caps_override={"max_string_chars": 200})
    assert changed["content_hash"] == _artifact()["content_hash"]
    second = canonical_bytes(changed)
    minted = write_if_changed(tmp_path, second, {"run": 3})
    assert minted is not None and minted.name == "v0002.json"
    # Immutability: v0001 is never edited.
    assert (tmp_path / "v0001.json").read_bytes() == first
