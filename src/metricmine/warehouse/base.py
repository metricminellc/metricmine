"""Engine-agnostic read-only warehouse protocol (D-11).

Spec: docs/spec/profiler.md §7. The profiler is the first consumer; the
shared query module serving gold extends the protocol later. These six
methods are the profiling surface, not the whole of D-11. Implementations
never execute DDL or DML.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ColumnStats:
    """Aggregates for one column; min/max are raw engine values.

    Whether min/max apply (numeric and temporal types only, spec §3) is the
    profiling layer's decision, not the warehouse's.
    """

    null_count: int
    distinct_count: int
    min: Any
    max: Any


class Warehouse(Protocol):
    """Read-only access to one warehouse file."""

    def list_tables(self, schema: str) -> list[str]: ...

    def columns(self, schema: str, table: str) -> list[tuple[str, str]]:
        """(name, physical_type) pairs in warehouse ordinal order."""
        ...

    def row_count(self, schema: str, table: str) -> int: ...

    def column_profile(self, schema: str, table: str, column: str) -> ColumnStats: ...

    def sample_values(
        self, schema: str, table: str, column: str, limit: int
    ) -> list[Any]:
        """First `limit` distinct non-null values in ascending order."""
        ...

    def duplicate_row_count(self, schema: str, table: str, columns: list[str]) -> int:
        """Row count minus distinct rows over the given columns."""
        ...
