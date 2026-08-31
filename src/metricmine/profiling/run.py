"""Profile the configured warehouse tables into committed artifacts.

Spec: docs/spec/profiler.md. Governing decisions: D-11 (read-only
warehouse protocol), D-04 (profiler outside dbt), D-03 (warehouse files).

Configuration comes from config/default.yaml's profiling block; this
script takes no arguments, the same posture as metricmine.ingest.
land_sample. Since the silver-pass scope amendment (spec §8), the block
carries a list of targets, one artifact directory per table, run by the
same code over each schema. Targets process sequentially and fail fast:
per-artifact atomicity is the writer's (temp-then-rename), and a rerun
after a mid-list failure converges because minting is write-if-changed.
The warehouse opens read-only; the run timestamp, the only time this
component touches, goes to the sidecar, never into artifact bytes.
"""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import yaml

from metricmine.profiling.build import AIRBYTE_PREFIX, SCHEMA_VERSION, profile_table
from metricmine.profiling.canonical import canonical_bytes
from metricmine.profiling.writer import write_if_changed
from metricmine.warehouse.duckdb import DuckDBWarehouse

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "config" / "default.yaml"

# Remedies named per schema (spec §8 failure modes): bronze lands via
# ingest; silver is built by dbt on top of it.
_REMEDIES = {
    "bronze": "run `make ingest` first",
    "silver": (
        "run `make ingest` and "
        "`uv run dbt build --project-dir transform --target local` first"
    ),
}


def _remedy(schema: str) -> str:
    return _REMEDIES.get(schema, "build the warehouse first")


def main() -> int:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())["profiling"]
    warehouse_path = (REPO_ROOT / cfg["warehouse_path"]).resolve()
    if not warehouse_path.is_file():
        print(
            f"ERROR: warehouse not found at {warehouse_path};"
            " run `make ingest` first"
        )
        return 1
    for target in cfg["targets"]:
        schema, table = target["schema"], target["table"]
        if table.startswith(AIRBYTE_PREFIX):
            print(
                f"ERROR: {schema}.{table} is PyAirbyte connector bookkeeping,"
                " not a data stream; the profiler skips _airbyte_* tables"
                " (docs/spec/profiler.md §8)"
            )
            return 1
        with DuckDBWarehouse(warehouse_path) as warehouse:
            if table not in warehouse.list_tables(schema):
                print(
                    f"ERROR: table {schema}.{table} not in the warehouse;"
                    f" {_remedy(schema)}"
                )
                return 1
            artifact = profile_table(warehouse, schema, table)

        profile_dir = REPO_ROOT / cfg["output_dir"] / f"{schema}.{table}"
        meta = {
            "duckdb_version": duckdb.__version__,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "profiler_schema_version": SCHEMA_VERSION,
            "python_version": platform.python_version(),
        }
        written = write_if_changed(profile_dir, canonical_bytes(artifact), meta)
        if written is None:
            print(
                f"unchanged: {profile_dir} already holds"
                f" {artifact['content_hash']}"
            )
        else:
            print(f"wrote {written} ({artifact['content_hash']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
