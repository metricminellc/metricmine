"""Profile builder: pure functions over warehouse-protocol results.

Spec: docs/spec/profiler.md §3 (artifact schema), §4 (determinism), §5
(token-budget caps). Nothing here touches time or randomness; run metadata
belongs to the sidecar (see writer/run). String ordering is Unicode
codepoint order via Python's sorted(), the spec's collation guarantee.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

from metricmine.profiling.canonical import content_hash
from metricmine.warehouse.base import ColumnStats, Warehouse

SCHEMA_VERSION = "1.0.0"

# Token-budget caps (spec §5): versioned profiler constants echoed in the
# artifact. Changing any of them is a profiler version change.
MAX_SAMPLE_VALUES = 10
MAX_DISTINCT_VALUES = 20
MAX_STRING_CHARS = 120
TRUNCATION_SUFFIX = "…[truncated]"

CAPS = {
    "max_distinct_values": MAX_DISTINCT_VALUES,
    "max_sample_values": MAX_SAMPLE_VALUES,
    "max_string_chars": MAX_STRING_CHARS,
}

AIRBYTE_PREFIX = "_airbyte_"

_NUMERIC_TYPES = {
    "DECIMAL",
    "NUMERIC",
    "TINYINT",
    "SMALLINT",
    "INTEGER",
    "BIGINT",
    "HUGEINT",
    "UTINYINT",
    "USMALLINT",
    "UINTEGER",
    "UBIGINT",
    "UHUGEINT",
    "FLOAT",
    "DOUBLE",
    "REAL",
}
_TEMPORAL_TYPES = {
    "DATE",
    "TIME",
    "TIME WITH TIME ZONE",
    "TIMESTAMP",
    "TIMESTAMP WITH TIME ZONE",
    "TIMESTAMP_S",
    "TIMESTAMP_MS",
    "TIMESTAMP_NS",
}


def _base_type(physical_type: str) -> str:
    # Strip type parameters only: DECIMAL(38,9) -> DECIMAL. Array/struct
    # suffixes survive, so INTEGER[] is never mistaken for INTEGER.
    return physical_type.upper().split("(")[0].strip()


def is_numeric(physical_type: str) -> bool:
    return _base_type(physical_type) in _NUMERIC_TYPES


def is_temporal(physical_type: str) -> bool:
    return _base_type(physical_type) in _TEMPORAL_TYPES


def normalize_value(value: Any) -> Any:
    """Normalize one observed value for serialization (spec §4).

    Floats round to 6 decimal places; temporal values become ISO 8601
    strings; strings over the cap truncate with the in-band marker.
    Anything else fails closed: nested and binary types have no canonical
    scalar form, and a Python repr must never reach a hashed artifact.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal | float):
        return round(float(value), 6)
    if isinstance(value, int):
        return value
    if isinstance(value, dt.datetime | dt.date | dt.time):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        value = str(value)
    if isinstance(value, str):
        if len(value) > MAX_STRING_CHARS:
            return value[:MAX_STRING_CHARS] + TRUNCATION_SUFFIX
        return value
    raise TypeError(
        f"unsupported observed value type {type(value).__name__}: the"
        " profiler serializes scalar values only (docs/spec/profiler.md §3)"
    )


def build_column_entry(
    name: str,
    physical_type: str,
    stats: ColumnStats,
    values: list[Any],
    row_count: int,
) -> dict:
    """One columns[] entry per spec §3. Inapplicable fields are omitted.

    `values` are the ascending distinct non-null values from the protocol;
    truncation applies after distinctness, so stats.distinct_count stays
    authoritative even when truncation collapses two long values.
    """
    entry: dict[str, Any] = {
        "name": name,
        "physical_type": physical_type,
        "null_count": stats.null_count,
        "null_rate": round(stats.null_count / row_count, 6) if row_count else 0.0,
        "distinct_count": stats.distinct_count,
        "is_airbyte_metadata": name.startswith(AIRBYTE_PREFIX),
    }
    if is_numeric(physical_type) or is_temporal(physical_type):
        if stats.min is not None:
            entry["min"] = normalize_value(stats.min)
        if stats.max is not None:
            entry["max"] = normalize_value(stats.max)
    try:
        ordered = sorted(values)
    except TypeError as exc:
        raise TypeError(
            f"column {name!r} ({physical_type}) has unorderable values:"
            " the profiler supports scalar column types only"
        ) from exc
    if stats.distinct_count <= MAX_DISTINCT_VALUES:
        entry["distinct_values"] = [normalize_value(v) for v in ordered]
    else:
        entry["sample_values"] = [
            normalize_value(v) for v in ordered[:MAX_SAMPLE_VALUES]
        ]
    return entry


def build_profile(
    schema: str,
    table: str,
    row_count: int,
    duplicate_count: int,
    column_entries: list[dict],
) -> dict:
    """Assemble the full artifact; content_hash covers dataset only."""
    dataset = {
        "columns": column_entries,
        "duplicate_row_rate": (
            round(duplicate_count / row_count, 6) if row_count else 0.0
        ),
        "row_count": row_count,
        "schema": schema,
        "table": table,
    }
    return {
        "caps": dict(CAPS),
        "content_hash": content_hash(dataset),
        "dataset": dataset,
        "schema_version": SCHEMA_VERSION,
    }


def profile_table(warehouse: Warehouse, schema: str, table: str) -> dict:
    """Profile one table through the read-only protocol (spec §3, §8).

    duplicate_row_rate is computed over source columns only, excluding
    _airbyte_* columns, which are profiled and flagged like any other.
    """
    cols = warehouse.columns(schema, table)
    row_count = warehouse.row_count(schema, table)
    source_columns = [n for n, _ in cols if not n.startswith(AIRBYTE_PREFIX)]
    duplicate_count = (
        warehouse.duplicate_row_count(schema, table, source_columns)
        if source_columns
        else 0
    )
    entries = []
    for name, physical_type in cols:
        stats = warehouse.column_profile(schema, table, name)
        # Always fetch up to the distinct cap; build_column_entry owns the
        # only cap branch, so the two sites cannot drift apart.
        values = warehouse.sample_values(schema, table, name, MAX_DISTINCT_VALUES)
        entries.append(
            build_column_entry(name, physical_type, stats, values, row_count)
        )
    return build_profile(schema, table, row_count, duplicate_count, entries)
