"""CI-surface tests for the ingestion config and connector config builder.

Network-free and warehouse-free: these pin the shape of config/default.yaml
and the source-file config dict (docs/spec/ingestion.md §2) without running
PyAirbyte. The end-to-end landing stays local (`make ingest` + the
local-marked smoke test). Since the multi-source fan-in (D-41) the block
carries a ``sources`` list, one entry per committed extract.
"""

import json
from pathlib import Path

import pytest
import yaml

from metricmine.ingest.land_sample import build_source_config, ingestion_sources

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _ingestion_cfg() -> dict:
    return yaml.safe_load((_REPO_ROOT / "config" / "default.yaml").read_text())[
        "ingestion"
    ]


def _retail() -> dict:
    return next(
        entry
        for entry in ingestion_sources(_ingestion_cfg())
        if entry["dataset_name"] == "online_retail_ii"
    )


def test_config_ingestion_block_shape():
    cfg = _ingestion_cfg()
    assert cfg["warehouse_path"] == "warehouse/metricmine.duckdb"
    assert cfg["schema"] == "bronze"
    sources = ingestion_sources(cfg)
    assert sources[0]["dataset_name"] == "online_retail_ii"
    for entry in sources:
        assert (_REPO_ROOT / entry["sample_csv"]).is_file(), entry["dataset_name"]
        assert (_REPO_ROOT / entry["sample_csv"]).stat().st_size <= 10 * 1024 * 1024


def test_every_source_lands_from_its_own_sample_directory():
    """One extract directory per source under data/samples/, named for
    the dataset it lands as, each carrying its README (D-15 as amended)."""
    for entry in ingestion_sources(_ingestion_cfg()):
        sample = _REPO_ROOT / entry["sample_csv"]
        assert sample.parent.name == entry["dataset_name"]
        assert (sample.parent / "README.md").is_file(), entry["dataset_name"]


def test_reader_options_pins_invoice_to_string():
    options = json.loads(_retail()["reader_options"])
    assert options["dtype"]["Invoice"] in ("str", "string", "object")


def test_build_source_config():
    entry = _retail()
    csv_path = (_REPO_ROOT / entry["sample_csv"]).resolve()
    source_config = build_source_config(entry, csv_path)
    assert source_config["format"] == "csv"
    assert source_config["provider"] == {"storage": "local"}
    assert Path(source_config["url"]).is_absolute()
    # reader_options passes through verbatim as the JSON string.
    assert source_config["reader_options"] == entry["reader_options"]


def test_build_source_config_omits_absent_reader_options():
    entry = {k: v for k, v in _retail().items() if k != "reader_options"}
    source_config = build_source_config(entry, Path("/tmp/sample.csv"))
    assert "reader_options" not in source_config


def test_legacy_single_source_block_reads_as_one_entry():
    """A pre-fan-in block (the single-source keys at the top level) still
    lands its one source; both forms at once is refused."""
    legacy = {
        "dataset_name": "x",
        "sample_csv": "data/samples/x/x.csv",
        "reader_options": "{}",
        "warehouse_path": "w",
        "schema": "bronze",
    }
    assert ingestion_sources(legacy) == [
        {"dataset_name": "x", "sample_csv": "data/samples/x/x.csv", "reader_options": "{}"}
    ]
    with pytest.raises(ValueError, match="both"):
        ingestion_sources({**legacy, "sources": [{"dataset_name": "y", "sample_csv": "y"}]})
    with pytest.raises(ValueError, match="unique"):
        ingestion_sources(
            {
                "sources": [
                    {"dataset_name": "y", "sample_csv": "a"},
                    {"dataset_name": "y", "sample_csv": "b"},
                ]
            }
        )
