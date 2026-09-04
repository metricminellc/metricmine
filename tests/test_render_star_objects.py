"""The star's per-category objects match the pattern their mapping renders.

D-41 (the multi-source proof) and F-42: the unified event star is
category-parameterized, so every category the star contract declares
carries the same three objects (the values and columns dimensions and
the fact) with the same conservation rules, rendered from its mapping
contract by ``scripts/render_star_objects.py``. This gate holds the
hand-approved contract to that pattern: for every configured mapping,
the rendered objects and the committed objects agree on every property
(name, types, required, primary key) and on every quality rule (type,
metric, severity, threshold, and the query modulo whitespace), and the
C3 coverage rule unions the category's columns dimension. Descriptions
are prose and stay free.

CI-lane, keyless: contracts and the renderer only.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import yaml

from metricmine.engine.reader import mapping_contract_paths

REPO = Path(__file__).resolve().parents[1]
STAR = REPO / "contracts" / "gold_unified_event_star.odcs.yaml"


def _load_renderer():
    spec = importlib.util.spec_from_file_location(
        "render_star_objects", REPO / "scripts" / "render_star_objects.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render_star_objects = _load_renderer()


def _rendered(mapping_path: Path) -> tuple[list[dict], str]:
    text = render_star_objects.render(mapping_path)
    body, _, trailer = text.partition("C3 union line for the registry")
    return yaml.safe_load(body), trailer


def _properties(obj: dict) -> list[tuple]:
    return [
        (
            p["name"],
            p.get("logicalType"),
            p.get("physicalType"),
            bool(p.get("required", False)),
            bool(p.get("primaryKey", False)),
        )
        for p in obj["properties"]
    ]


def _rules(obj: dict) -> list[tuple]:
    return [
        (
            r.get("type"),
            r.get("metric"),
            r.get("severity"),
            r.get("mustBe", r.get("mustBeGreaterThan")),
            re.sub(r"\s+", " ", str(r.get("query", "")).strip()),
        )
        for r in obj.get("quality", [])
    ]


def _configured_mappings() -> list[Path]:
    cfg = yaml.safe_load((REPO / "config" / "default.yaml").read_text(encoding="utf-8"))
    return [REPO / p for p in mapping_contract_paths(cfg["engine"])]


def test_every_category_matches_its_rendered_pattern() -> None:
    star = yaml.safe_load(STAR.read_text(encoding="utf-8"))
    committed = {o["name"]: o for o in star["schema"]}
    registry = committed["context_registry"]
    c3 = " ".join(
        str(r.get("query", "")) for r in registry.get("quality", []) if "UNION" in str(r.get("query", ""))
    )
    mappings = _configured_mappings()
    assert mappings, "the engine configuration names at least one mapping contract"
    for mapping_path in mappings:
        objects, _trailer = _rendered(mapping_path)
        assert len(objects) == 3, mapping_path.name
        for obj in objects:
            assert obj["name"] in committed, f"{obj['name']} is not declared in the star"
            assert _properties(obj) == _properties(committed[obj["name"]]), obj["name"]
            assert _rules(obj) == _rules(committed[obj["name"]]), obj["name"]
        category = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))["schema"][0]["name"]
        assert f"ref('dim_{category}_columns')" in c3, f"C3 does not union dim_{category}_columns"


def test_renderer_refuses_other_grains(tmp_path) -> None:
    mapping = yaml.safe_load(
        (REPO / "contracts" / "gold_invoice_lines_mapping.odcs.yaml").read_text(encoding="utf-8")
    )
    mapping["schema"][0]["grain"] = {"type": "aggregated"}
    path = tmp_path / "gold_probe_mapping.odcs.yaml"
    path.write_text(yaml.safe_dump(mapping, sort_keys=False), encoding="utf-8")
    try:
        render_star_objects.render(path)
    except SystemExit as exc:
        assert "transaction grain" in str(exc)
    else:
        raise AssertionError("the renderer must refuse a grain it does not cover")
