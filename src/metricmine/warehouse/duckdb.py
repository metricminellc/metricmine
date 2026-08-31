"""DuckDB implementation of the read-only warehouse protocol (D-11).

Spec: docs/spec/profiler.md §7. The connection opens with read_only=True:
no DDL, no DML; every method is a SELECT. Sample ordering relies on
DuckDB's default binary collation; the profiling layer re-sorts in Python
as the spec's codepoint-order guarantee (§4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from metricmine.warehouse.base import ColumnStats


def _ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class DuckDBWarehouse:
    def __init__(self, path: Path | str) -> None:
        self._con = duckdb.connect(str(path), read_only=True)
        # Session setting, not DML: pin the zone so TIMESTAMPTZ values
        # render identically on every machine (spec §4 byte-determinism).
        self._con.execute("set timezone = 'UTC'")

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> DuckDBWarehouse:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _rel(self, schema: str, table: str) -> str:
        return f"{_ident(schema)}.{_ident(table)}"

    def list_tables(self, schema: str) -> list[str]:
        rows = self._con.execute(
            "select table_name from information_schema.tables"
            " where table_schema = ? order by table_name",
            [schema],
        ).fetchall()
        return [row[0] for row in rows]

    def columns(self, schema: str, table: str) -> list[tuple[str, str]]:
        rows = self._con.execute(
            "select column_name, data_type from information_schema.columns"
            " where table_schema = ? and table_name = ?"
            " order by ordinal_position",
            [schema, table],
        ).fetchall()
        return [(row[0], row[1]) for row in rows]

    def relation_kinds(self, schema: str) -> dict[str, str]:
        rows = self._con.execute(
            "select table_name, table_type from information_schema.tables"
            " where table_schema = ? order by table_name",
            [schema],
        ).fetchall()
        return {
            row[0]: ("view" if row[1] == "VIEW" else "table") for row in rows
        }

    def row_count(self, schema: str, table: str) -> int:
        (count,) = self._con.execute(
            f"select count(*) from {self._rel(schema, table)}"
        ).fetchone()
        return count

    def column_profile(self, schema: str, table: str, column: str) -> ColumnStats:
        col = _ident(column)
        null_count, distinct_count, min_value, max_value = self._con.execute(
            f"select count(*) - count({col}), count(distinct {col}),"
            f" min({col}), max({col}) from {self._rel(schema, table)}"
        ).fetchone()
        return ColumnStats(null_count, distinct_count, min_value, max_value)

    def sample_values(
        self, schema: str, table: str, column: str, limit: int
    ) -> list[Any]:
        col = _ident(column)
        rows = self._con.execute(
            f"select distinct {col} from {self._rel(schema, table)}"
            f" where {col} is not null order by {col} limit {int(limit)}"
        ).fetchall()
        return [row[0] for row in rows]

    def duplicate_row_count(
        self, schema: str, table: str, columns: list[str]
    ) -> int:
        cols = ", ".join(_ident(c) for c in columns)
        rel = self._rel(schema, table)
        (excess,) = self._con.execute(
            f"select count(*) - (select count(*) from"
            f" (select distinct {cols} from {rel})) from {rel}"
        ).fetchone()
        return excess
