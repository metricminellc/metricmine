"""Profile the configured bronze table into a committed artifact.

Spec: docs/spec/profiler.md. Governing decisions: D-11 (read-only
warehouse protocol), D-04 (profiler outside dbt), D-03 (warehouse files).

Configuration comes from config/default.yaml's profiling block; this
script takes no arguments, the same posture as metricmine.ingest.
land_sample. The warehouse opens read-only; the run timestamp — the only
time this component touches — goes to the sidecar, never into artifact
bytes.
"""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import yaml

from metricmine.profiling.build import SCHEMA_VERSION, profile_table
from metricmine.profiling.canonical import canonical_bytes
from metricmine.profiling.writer import write_if_changed
from metricmine.warehouse.duckdb import DuckDBWarehouse

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "config" / "default.yaml"


def main() -> int:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())["profiling"]
    warehouse_path = (REPO_ROOT / cfg["warehouse_path"]).resolve()
    if not warehouse_path.is_file():
        print(
            f"ERROR: warehouse not found at {warehouse_path};"
            " run `make ingest` first"
        )
        return 1
    schema, table = cfg["schema"], cfg["table"]
    with DuckDBWarehouse(warehouse_path) as warehouse:
        if table not in warehouse.list_tables(schema):
            print(
                f"ERROR: table {schema}.{table} not in the warehouse;"
                " run `make ingest` first"
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
        print(f"unchanged: {profile_dir} already holds {artifact['content_hash']}")
    else:
        print(f"wrote {written} ({artifact['content_hash']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
