"""The multi-source selectors and the agreement study across stances (D-41).

Keyless. The cleanup stance takes a bronze source and the propose stance
a silver table; each derives its profile directory and its target
contract from the selector; the eval fixtures name a source or table
plus an oracle; the mapping scorer agrees with a committed mapping
contract in full when the draft is that contract, and names every
mismatch when it is not. The live study itself is Justin's run with a
key (make eval-agents); everything below proves the plumbing that run
depends on.
"""

from __future__ import annotations

import copy
import os
import subprocess
import sys
from pathlib import Path

import yaml

from metricmine.agents import agreement, mapping_proposer, silver_proposer
from metricmine.agents import eval as eval_lane
from metricmine.agents.harness import load_agents_config

REPO_ROOT = Path(__file__).resolve().parents[2]

AVIATION_SOURCES = (
    "nyc_flights",
    "nyc_weather",
    "nyc_airlines",
    "nyc_planes",
    "ourairports_airports",
    "ourairports_runways",
)


def test_cleanup_spec_derives_from_the_source() -> None:
    for source in AVIATION_SOURCES:
        spec = silver_proposer.build_spec(REPO_ROOT, source=source)
        assert spec.stance == "cleanup"
        assert spec.profile_dir == REPO_ROOT / "profiles" / f"bronze.{source}"
        assert spec.profile_dir.is_dir(), f"{source}: the profile the arc minted"
        assert spec.target_contract == REPO_ROOT / "contracts" / f"silver_{source}.odcs.yaml"
        assert spec.target_contract.is_file(), f"{source}: the human-authored contract"
    default = silver_proposer.build_spec(REPO_ROOT)
    assert default.profile_dir == REPO_ROOT / "profiles" / "bronze.online_retail_ii"
    assert default.target_contract == REPO_ROOT / "contracts" / "silver_invoice_lines.odcs.yaml"
    explicit = silver_proposer.build_spec(REPO_ROOT, source="nyc_flights", target="silver_flights_alt")
    assert explicit.target_contract.name == "silver_flights_alt.odcs.yaml"


def test_propose_spec_derives_from_the_table() -> None:
    for table, target in (
        ("silver_flights", "gold_flights_mapping"),
        ("silver_airport_weather", "gold_airport_weather_mapping"),
    ):
        spec = mapping_proposer.build_spec(REPO_ROOT, table=table)
        assert spec.stance == "propose"
        assert spec.profile_dir == REPO_ROOT / "profiles" / f"silver.{table}"
        assert spec.profile_dir.is_dir()
        assert spec.target_contract == REPO_ROOT / "contracts" / f"{target}.odcs.yaml"
        assert spec.target_contract.is_file()
    assert mapping_proposer.default_target("silver_flights") == "gold_flights_mapping"
    assert mapping_proposer.default_target("orders") == "gold_orders_mapping"
    default = mapping_proposer.build_spec(REPO_ROOT)
    assert default.profile_dir == REPO_ROOT / "profiles" / "silver.silver_invoice_lines"


def test_eval_fixtures_cover_the_family_with_oracles() -> None:
    fixtures = eval_lane.load_fixtures(REPO_ROOT)
    by_label = {f["label"]: f for f in fixtures}
    for source in AVIATION_SOURCES:
        label = f"silver-cleanup-{source.replace('_', '-')}"
        fixture = by_label[label]
        assert fixture["proposer"] == "silver" and fixture["source"] == source
        assert (REPO_ROOT / fixture["profile"]).is_file()
        assert (REPO_ROOT / fixture["oracle"]).is_file()
        spec = eval_lane._build(REPO_ROOT, fixture)
        assert spec.target_contract == REPO_ROOT / fixture["oracle"]
    for table, label in (
        ("silver_flights", "mapping-propose-flights"),
        ("silver_airport_weather", "mapping-propose-airport-weather"),
    ):
        fixture = by_label[label]
        assert fixture["proposer"] == "mapping" and fixture["table"] == table
        assert (REPO_ROOT / fixture["profile"]).is_file()
        spec = eval_lane._build(REPO_ROOT, fixture)
        assert spec.target_contract == REPO_ROOT / fixture["oracle"]
    # The three original fixtures stand unchanged, without an oracle.
    for label in ("silver-cleanup-online-retail", "mapping-propose-invoice-lines", "silver-cleanup-messy-orders"):
        assert "oracle" not in by_label[label]
    assert len(fixtures) == 11


def test_eval_fixture_profiles_are_the_newest_artifacts() -> None:
    """Each fixture pins the artifact the oracle contract cites, so the
    study runs over the same evidence the human authored from."""
    fixtures = eval_lane.load_fixtures(REPO_ROOT)
    for fixture in fixtures:
        if "oracle" not in fixture:
            continue
        profile = REPO_ROOT / fixture["profile"]
        oracle = yaml.safe_load((REPO_ROOT / fixture["oracle"]).read_text(encoding="utf-8"))
        cited = next(p["value"] for p in oracle["customProperties"] if p["property"] == "profileHash")
        import json

        assert json.loads(profile.read_text(encoding="utf-8"))["content_hash"] == cited, fixture["label"]


def _mapping(name: str) -> dict:
    return yaml.safe_load((REPO_ROOT / "contracts" / f"{name}.odcs.yaml").read_text(encoding="utf-8"))


def test_mapping_scorer_agrees_in_full_with_itself() -> None:
    for name in ("gold_flights_mapping", "gold_airport_weather_mapping", "gold_invoice_lines_mapping"):
        oracle = _mapping(name)
        result = agreement.score_mapping(copy.deepcopy(oracle), oracle)
        props = len(oracle["schema"][0]["properties"])
        assert result["first_class_checks"] == {
            "agree": props * 4,
            "checked": props * 4,
            "per_field": {
                "mappingRole": f"{props}/{props}",
                "logicalType": f"{props}/{props}",
                "physicalType": f"{props}/{props}",
                "required": f"{props}/{props}",
            },
        }
        assert result["properties"]["ordinal_order_equal"] is True
        assert all(result["header"].values())
        assert result["roles"] == {"dimensions_equal": True, "measures_equal": True}
        assert result["identifiers_equal"] is True
        assert result["mismatches"] == []
        assert agreement.summary_lines_mapping(result)[-1] == "  mismatches: none"


def test_mapping_scorer_names_every_disagreement() -> None:
    oracle = _mapping("gold_flights_mapping")
    draft = copy.deepcopy(oracle)
    category = draft["schema"][0]
    category["timeGrain"] = "day"
    category["properties"][0]["mappingRole"] = "measure"
    dropped = category["properties"].pop()
    category["properties"].append({"name": "extra_col", "mappingRole": "dimension", "logicalType": "string", "physicalType": "VARCHAR"})
    category["grain"]["degenerateIdentifiers"][0]["of"] = ["flight_date"]
    result = agreement.score_mapping(draft, oracle)
    joined = "\n".join(result["mismatches"])
    assert f"{dropped['name']}: missing from the draft" in joined
    assert "extra_col: extra in the draft" in joined
    assert "timeGrain: oracle='hour' draft='day'" in joined
    assert f"{oracle['schema'][0]['properties'][0]['name']}.mappingRole" in joined
    assert "degenerateIdentifiers:" in joined
    assert result["header"]["timeGrain"] is False
    assert result["identifiers_equal"] is False
    assert result["roles"]["measures_equal"] is False
    lines = agreement.summary_lines_mapping(result)
    assert lines[0].startswith("agreement study (n=1) against oracle 'gold_flights_mapping'")
    assert "  mismatches:" in lines


def _keyless_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("MM_PROPOSER_MODEL", None)
    return env


def test_missing_oracle_refuses_before_any_call() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "metricmine.agents", "propose", "silver", "--source", "nyc_flights", "--oracle", "contracts/nope.odcs.yaml"],
        capture_output=True,
        text=True,
        env=_keyless_env(),
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 1
    assert "does not exist" in proc.stderr


def test_keyless_selector_run_refuses_before_any_call() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "metricmine.agents", "propose", "mapping", "--table", "silver_flights"],
        capture_output=True,
        text=True,
        env=_keyless_env(),
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 1
    assert "ANTHROPIC_API_KEY" in proc.stderr


def test_config_stances_are_unchanged_for_the_default_tables() -> None:
    cfg = load_agents_config(REPO_ROOT)
    assert cfg["silver"]["stances"]["cleanup"]["profile_dir"] == "profiles/bronze.online_retail_ii"
    assert cfg["mapping"]["stances"]["propose"]["profile_dir"] == "profiles/silver.silver_invoice_lines"
