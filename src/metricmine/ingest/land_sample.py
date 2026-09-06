"""Land the committed sample extracts into bronze via PyAirbyte.

Spec: docs/spec/ingestion.md. Governing decisions: D-15 (committed
samples), D-03 (gitignored working warehouse), D-41 (the multi-source
proof: one connector type, many files).

The Airbyte source-file connector reads each committed CSV and
full-refresh replaces its bronze table in the working DuckDB warehouse,
one stream per source, all through the same connector venv. Bronze is
evidence: no renames, no casts, no transforms; _airbyte_* columns land
as-is. Configuration comes from the ingestion block of
config/default.yaml, whose ``sources`` list carries one entry per
committed extract; this script takes no arguments, the same posture as
scripts/fetch_sample.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import airbyte as ab
import yaml
from airbyte.caches import DuckDBCache

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "config" / "default.yaml"


def build_source_config(cfg: dict, csv_path: Path) -> dict:
    """Build the source-file connector config from one sources entry.

    Config keys verified against connector docs v0.6.0 (spec §2). PyAirbyte
    runs the connector in a local venv, so a plain absolute path is used;
    the Docker-era "/local/" prefix from the platform docs does not apply.
    """
    source_config = {
        "dataset_name": cfg["dataset_name"],
        "format": "csv",
        "url": str(csv_path),
        "provider": {"storage": "local"},
    }
    if cfg.get("reader_options"):
        # JSON string of pandas read_csv options, passed through as-is.
        source_config["reader_options"] = cfg["reader_options"]
    return source_config


def ingestion_sources(cfg: dict) -> list[dict]:
    """The ordered source list of the ingestion block, fail-closed.

    ``sources`` is the form since the multi-source fan-in (D-41); a block
    that still carries the single-source keys (``dataset_name`` and
    ``sample_csv`` at the top level) reads as a one-entry list so a
    pre-fan-in config keeps working. Both forms at once is an error, and
    every entry names a distinct dataset.
    """
    sources = cfg.get("sources")
    legacy = "dataset_name" in cfg or "sample_csv" in cfg
    if sources is not None and legacy:
        raise ValueError(
            "ingestion block names both sources and the single-source keys;"
            " keep the list only"
        )
    if sources is None:
        if not legacy:
            raise ValueError("ingestion block names no sources")
        sources = [
            {
                key: cfg[key]
                for key in ("dataset_name", "sample_csv", "reader_options")
                if key in cfg
            }
        ]
    if not isinstance(sources, list) or not sources:
        raise ValueError("ingestion.sources must be a non-empty list")
    names = [entry["dataset_name"] for entry in sources]
    if len(set(names)) != len(names):
        raise ValueError(f"ingestion.sources dataset names must be unique: {names}")
    return sources


def main() -> int:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())["ingestion"]
    warehouse_path = (REPO_ROOT / cfg["warehouse_path"]).resolve()
    sources = ingestion_sources(cfg)
    csv_paths = {}
    for entry in sources:
        csv_path = (REPO_ROOT / entry["sample_csv"]).resolve()
        if not csv_path.is_file():
            print(
                f"ERROR: sample CSV for {entry['dataset_name']} not found at"
                f" {csv_path}; run its fetch script under scripts/"
            )
            return 1
        csv_paths[entry["dataset_name"]] = csv_path
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    for entry in sources:
        source = ab.get_source(
            "source-file",
            config=build_source_config(entry, csv_paths[entry["dataset_name"]]),
        )
        source.check()
        source.select_all_streams()
        result = source.read(
            cache=DuckDBCache(
                db_path=str(warehouse_path), schema_name=cfg["schema"]
            ),
            write_strategy="replace",
            force_full_refresh=True,
        )
        for name, dataset in result.streams.items():
            counts[name] = len(dataset)

    print(f"landed {counts} into {cfg['schema']} of {warehouse_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
