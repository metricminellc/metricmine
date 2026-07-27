"""CI-surface tests for the ingestion config and connector config builder.

Network-free and warehouse-free: these pin the shape of config/default.yaml
and the source-file config dict (docs/spec/ingestion.md §2) without running
PyAirbyte. The end-to-end landing stays local (`make ingest` + the
local-marked smoke test).
"""

import json
from pathlib import Path

import yaml

from metricmine.ingest.land_sample import build_source_config

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _ingestion_cfg() -> dict:
    return yaml.safe_load((_REPO_ROOT / "config" / "default.yaml").read_text())[
        "ingestion"
    ]


def test_config_ingestion_block_shape():
    cfg = _ingestion_cfg()
    assert cfg["dataset_name"] == "online_retail_ii"
    assert (_REPO_ROOT / cfg["sample_csv"]).is_file()
    assert cfg["warehouse_path"] == "warehouse/metricmine.duckdb"
    assert cfg["schema"] == "bronze"


def test_reader_options_pins_invoice_to_string():
    options = json.loads(_ingestion_cfg()["reader_options"])
    assert options["dtype"]["Invoice"] in ("str", "string", "object")


def test_build_source_config():
    cfg = _ingestion_cfg()
    csv_path = (_REPO_ROOT / cfg["sample_csv"]).resolve()
    source_config = build_source_config(cfg, csv_path)
    assert source_config["format"] == "csv"
    assert source_config["provider"] == {"storage": "local"}
    assert Path(source_config["url"]).is_absolute()
    # reader_options passes through verbatim as the JSON string.
    assert source_config["reader_options"] == cfg["reader_options"]


def test_build_source_config_omits_absent_reader_options():
    cfg = {k: v for k, v in _ingestion_cfg().items() if k != "reader_options"}
    source_config = build_source_config(cfg, Path("/tmp/sample.csv"))
    assert "reader_options" not in source_config
