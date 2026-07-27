"""Land the committed Online Retail II sample into bronze via PyAirbyte.

Spec: docs/spec/ingestion.md. Governing decisions: D-15 (committed sample),
D-03 (gitignored working warehouse).

The Airbyte source-file connector reads the committed CSV and full-refresh
replaces bronze.online_retail_ii in the working DuckDB warehouse. Bronze is
evidence: no renames, no casts, no transforms; _airbyte_* columns land as-is.
Configuration comes from config/default.yaml; this script takes no arguments,
the same posture as scripts/fetch_sample.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import airbyte as ab
import yaml
from airbyte.caches import DuckDBCache

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "config" / "default.yaml"


def main() -> int:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())["ingestion"]
    csv_path = (REPO_ROOT / cfg["sample_csv"]).resolve()
    warehouse_path = (REPO_ROOT / cfg["warehouse_path"]).resolve()
    if not csv_path.is_file():
        print(f"ERROR: sample CSV not found at {csv_path}; run scripts/fetch_sample.py")
        return 1
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)

    # source-file config keys verified against connector docs v0.6.0 (spec §2).
    # PyAirbyte runs the connector in a local venv, so a plain absolute path is
    # used — the Docker-era "/local/" prefix from the platform docs does not
    # apply here.
    source_config = {
        "dataset_name": cfg["dataset_name"],
        "format": "csv",
        "url": str(csv_path),
        "provider": {"storage": "local"},
    }
    if cfg.get("reader_options"):
        # JSON string of pandas read_csv options, passed through as-is.
        source_config["reader_options"] = cfg["reader_options"]
    source = ab.get_source("source-file", config=source_config)
    source.check()
    source.select_all_streams()
    result = source.read(
        cache=DuckDBCache(db_path=str(warehouse_path), schema_name=cfg["schema"]),
        write_strategy="replace",
        force_full_refresh=True,
    )

    counts = {name: len(dataset) for name, dataset in result.streams.items()}
    print(f"landed {counts} into {cfg['schema']} of {warehouse_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
