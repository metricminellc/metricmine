"""Deterministic grain verification against the live warehouse (D-35).

Grain proposed by any stance is unverified until this measurement runs
(F-10: many column subsets are statistically plausible keys; only the
warehouse settles one). NOT an agent (D-10 Amendment G, CLAUDE.md rule
15): no model call, no network, no loop; one read-only protocol call
per candidate tuple and no writes. The measurement is
`duplicate_row_count` over the declared keys, plus the same count over
each single key so the operator sees why the tuple is needed. This is
a CLI, not the stdio server: stdout carries results and stderr
diagnostics (rule 18's stdout discipline governs the server only).
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from metricmine.warehouse.duckdb import DuckDBWarehouse


def _warehouse_path(repo_root: Path) -> Path:
    config = yaml.safe_load(
        (repo_root / "config" / "default.yaml").read_text(encoding="utf-8")
    )
    return repo_root / config["profiling"]["warehouse_path"]


def run(
    repo_root: Path, table: str, keys: list[str], schema: str = "silver"
) -> int:
    """0: zero duplicate rows over the keys. 1: duplicates or a
    precondition unmet (named on stderr)."""
    warehouse_path = _warehouse_path(repo_root)
    if not warehouse_path.is_file():
        print(
            f"error: no warehouse at {warehouse_path}; build it first "
            f"(make ingest, then dbt build)",
            file=sys.stderr,
        )
        return 1
    if not keys:
        print("error: at least one grain key is required", file=sys.stderr)
        return 1
    with DuckDBWarehouse(warehouse_path) as warehouse:
        if table not in warehouse.list_tables(schema):
            print(
                f"error: no relation {schema}.{table} in the warehouse",
                file=sys.stderr,
            )
            return 1
        columns = {name for name, _ in warehouse.columns(schema, table)}
        missing = sorted(set(keys) - columns)
        if missing:
            print(
                f"error: key(s) not columns of {schema}.{table}: "
                f"{', '.join(missing)}",
                file=sys.stderr,
            )
            return 1
        duplicates = warehouse.duplicate_row_count(schema, table, keys)
        print(f"duplicate rows over {keys}: {duplicates}")
        if len(keys) > 1:
            for key in keys:
                single = warehouse.duplicate_row_count(schema, table, [key])
                print(f"duplicate rows over {[key]}: {single}")
    joined = ", ".join(keys)
    if duplicates == 0:
        print(f"verify-grain: PASS ({schema}.{table} is unique over ({joined}))")
        return 0
    print(
        f"verify-grain: FAIL ({duplicates} duplicate row(s) over "
        f"({joined}); the declared grain does not hold)"
    )
    return 1
