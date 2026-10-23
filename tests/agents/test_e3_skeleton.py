"""The skeleton (E3b, experiment branch; docs/experiments/e3/KEY.md Section
3): code writes the machine half, the model declares the judgment, and the
UNCHANGED validator judges the result, keyless.

For every committed silver profile the describe skeleton plus a minimal
judgment passes validate_describe with zero errors; a perturbed machine
half is refused by the validator exactly as at head (the stop condition
the thread names: the validators still enforce equality). The amend
skeleton over the committed 1.2.0 contract plus the example judgment
passes validate_amend and derives 1.3.0; a narrowing is refused without
the flag; an addition enters optional whatever the judgment says (F-28).
A judgment that names a column the skeleton does not carry raises
SkeletonError, which the harness feeds back as a judgment error.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from metricmine.agents import e3, harness, skeleton
from metricmine.agents.harness import SkeletonError
from metricmine.agents.validate import validate_amend, validate_describe

from .e3_support import (
    REPO_ROOT,
    amend_judgment,
    amend_proposal,
    describe_judgment,
    describe_proposal,
    profile,
)

SILVER_PROFILES = sorted(p for p in REPO_ROOT.glob("profiles/silver.*/v[0-9][0-9][0-9][0-9].json"))
COMMITTED_120 = REPO_ROOT / "docs/experiments/e3/fixtures/silver_invoice_lines@1.2.0.odcs.yaml"
JUDGMENT_SCHEMA = REPO_ROOT / "docs/spec/agent-layer/e3/table-contract-judgment.schema.json"
PROPOSAL_SCHEMA = REPO_ROOT / "docs/spec/agent-layer/table-contract-proposal.schema.json"


def _committed() -> dict:
    return yaml.safe_load(COMMITTED_120.read_text(encoding="utf-8"))


def _proposal_validator() -> Draft202012Validator:
    local, _ = harness.load_proposal_schema(PROPOSAL_SCHEMA)
    return Draft202012Validator(local)


@pytest.mark.parametrize("path", SILVER_PROFILES, ids=[f"{p.parent.name}/{p.stem}" for p in SILVER_PROFILES])
def test_describe_skeleton_plus_a_judgment_passes_the_unchanged_validator(path: Path) -> None:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    bare = skeleton.describe_skeleton(artifact)
    assert [c["name"] for c in bare["columns"]] == [c["name"] for c in artifact["dataset"]["columns"]]
    assert all(c["description"] == "" for c in bare["columns"])
    assert [r["kind"] for r in bare["quality_rules"]] == ["row_count_positive", "grain_unique"]
    # The bare skeleton lacks only the judgment: the grain.
    bare_errors = validate_describe(bare, artifact)
    assert bare_errors == ["completeness: at least one grain key is required"]
    assert e3.classify_errors("describe", bare_errors) == (0, 1, 0)
    full = describe_proposal(artifact)
    errors = validate_describe(full, artifact)
    assert errors == [], errors
    assert not _proposal_validator().iter_errors(full) or list(_proposal_validator().iter_errors(full)) == []
    machine, total = skeleton.machine_half_chars(full)
    assert 0 < machine < total


@pytest.mark.parametrize("path", SILVER_PROFILES[:3], ids=[f"{p.parent.name}/{p.stem}" for p in SILVER_PROFILES[:3]])
def test_a_perturbed_machine_half_is_still_refused_by_the_validator(path: Path) -> None:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    full = describe_proposal(artifact)
    first = full["columns"][0]

    def errors_after(mutate) -> list[str]:  # noqa: ANN001
        changed = copy.deepcopy(full)
        mutate(changed)
        found = validate_describe(changed, artifact)
        assert found, "the validator accepted a perturbed machine half"
        machine, _, _ = e3.classify_errors("describe", found)
        assert machine >= 1, found
        return found

    errors_after(lambda p: p["columns"][0].update(physical_type=first["physical_type"] + "_X"))
    errors_after(lambda p: p["columns"][0].update(required=not first["required"]))
    errors_after(lambda p: p["columns"].pop())
    errors_after(lambda p: p["columns"].reverse() if len(p["columns"]) > 1 else p["columns"].pop())
    errors_after(lambda p: p["quality_rules"].pop(0))
    errors_after(lambda p: p.update(target_table=p["target_table"] + "_x"))


def test_a_judgment_that_names_an_unknown_column_is_a_skeleton_error() -> None:
    artifact = profile("profiles/silver.silver_nyc_airlines/v0001.json")
    judgment = describe_judgment(artifact)
    judgment["column_prose"].append({"name": "ghost", "description": "x", "rationale": "y"})
    with pytest.raises(SkeletonError, match="column_prose names 'ghost'"):
        skeleton.apply_judgment(skeleton.describe_skeleton(artifact), judgment)


def test_describe_refuses_a_missing_or_duplicated_column_and_amend_refuses_prose() -> None:
    artifact = profile("profiles/silver.silver_nyc_airlines/v0001.json")
    bare = skeleton.describe_skeleton(artifact)
    judgment = describe_judgment(artifact)
    judgment["column_prose"].pop()
    with pytest.raises(SkeletonError, match="leaves 1 profiled column\\(s\\) undescribed"):
        skeleton.apply_judgment(bare, judgment)
    judgment = describe_judgment(artifact)
    judgment["column_prose"].append(dict(judgment["column_prose"][0]))
    with pytest.raises(SkeletonError, match="twice; every column is described exactly once"):
        skeleton.apply_judgment(bare, judgment)
    committed = _committed()
    judgment = amend_judgment()
    judgment["column_prose"] = [{"name": "country", "description": "x", "rationale": "y"}]
    with pytest.raises(SkeletonError, match="amend carries no column_prose"):
        skeleton.apply_judgment(skeleton.amend_skeleton(committed), judgment)
    # Under amend the stated grain is checked against the committed grain
    # plus the declared changes, never applied on its own.
    judgment = amend_judgment()
    judgment["grain_keys"] = ["invoice_id"]
    with pytest.raises(SkeletonError, match="the grain moves only by a declared grain_change"):
        skeleton.apply_judgment(skeleton.amend_skeleton(committed), judgment)
    judgment = amend_judgment()
    judgment["grain_keys"] = []
    assert skeleton.apply_judgment(skeleton.amend_skeleton(committed), judgment)["grain_keys"] == [
        "invoice_id", "stock_code", "quantity", "unit_price"
    ]


def test_describe_refuses_the_amend_channels_and_a_stance_mismatch() -> None:
    artifact = profile("profiles/silver.silver_nyc_airlines/v0001.json")
    bare = skeleton.describe_skeleton(artifact)
    judgment = describe_judgment(artifact)
    judgment["changes"] = [{"kind": "no_change", "column": "", "before": "", "after": "", "rationale": "x"}]
    with pytest.raises(SkeletonError, match="describe carries no added_columns and no changes"):
        skeleton.apply_judgment(bare, judgment)
    judgment = describe_judgment(artifact)
    judgment["stance"] = "amend"
    with pytest.raises(SkeletonError, match="stance 'amend' is not the run's stance 'describe'"):
        skeleton.apply_judgment(bare, judgment)


def test_the_harness_feeds_a_skeleton_error_back_as_a_judgment_error(tmp_path: Path) -> None:
    from metricmine.agents import silver_proposer

    from .e3_support import RoutingClient, lint_ok, mirrored_root

    root = mirrored_root(tmp_path)
    artifact = profile("profiles/silver.silver_nyc_airlines/v0001.json")
    bad = describe_judgment(artifact)
    bad["column_prose"][0]["name"] = "ghost"
    good = describe_judgment(artifact)
    client = RoutingClient({"silver_nyc_airlines": [json.dumps(bad), json.dumps(good)]})
    arms = e3.load_arms(root)
    built = e3.build_run(root, arms, "B", "describe-silver-flights")
    # The B arm's describe spec (the e3 prompt, the judgment schema, the
    # skeleton), pointed at the smallest silver table.
    spec = dataclasses.replace(
        built["spec"],
        profile_dir=root / "profiles/silver.silver_nyc_airlines",
        target_contract=root / "contracts/silver_nyc_airlines.odcs.yaml",
    )
    report: dict = {}
    code = harness.run_proposer(
        spec, root, profile=str(root / "profiles/silver.silver_nyc_airlines/v0001.json"),
        client=client, lint_runner=lint_ok, report=report, quiet=True,
    )
    assert code == 0, report["record"]["validation"]["errors"]
    record = report["record"]
    log = record["validation"]["attempt_log"]
    assert len(log) == 2
    assert log[0]["schema_pass"] is True
    assert log[0]["errors"] == ["judgment: column_prose names 'ghost', which the skeleton does not carry; "
                                "the machine half is written by code and a judgment only describes it"]
    assert e3.classify_errors("describe", log[0]["errors"]) == (0, 1, 0)
    assert record["skeleton"] is True
    run_dir = Path(report["run_dir"])
    assert json.loads((run_dir / "judgment.json").read_text(encoding="utf-8")) == good
    proposal = json.loads((run_dir / "proposal.json").read_text(encoding="utf-8"))
    assert proposal == skeleton.apply_judgment(skeleton.describe_skeleton(artifact), good)
    assert "The judgment failed validation. Errors:\njudgment: column_prose names 'ghost'" in (
        client.calls[1]["messages"][2]["content"]
    )
    assert silver_proposer.NAME == record["agent"]["name"]


def test_amend_skeleton_plus_the_example_judgment_derives_1_3_0() -> None:
    committed = _committed()
    bare = skeleton.amend_skeleton(committed)
    assert bare["proposed_version"] == "1.2.0"
    assert bare["target_table"] == "silver_invoice_lines" and bare["target_schema"] == "silver"
    assert [c["name"] for c in bare["columns"]] == [p["name"] for p in committed["schema"][0]["properties"]]
    assert bare["grain_keys"] == ["invoice_id", "stock_code", "quantity", "unit_price"] or bare["grain_keys"]
    fresh = profile("profiles/silver.silver_invoice_lines/v0002.json")
    full = amend_proposal(committed)
    assert full["proposed_version"] == "1.3.0"
    errors = validate_amend(full, fresh, committed, allow_relaxation=False)
    assert errors == [], errors
    captured_at = next(c for c in full["columns"] if c["name"] == "captured_at")
    assert captured_at["required"] is True
    assert "required" in captured_at["description"]
    assert [c["kind"] for c in full["changes"]] == ["required_change", "description_change"]
    assert full["purpose"] == str(committed["description"]["purpose"])


def test_an_addition_enters_optional_whatever_the_judgment_says() -> None:
    committed = _committed()
    judgment = amend_judgment()
    judgment["added_columns"] = [{
        "name": "line_note", "logical_type": "string", "physical_type": "VARCHAR",
        "required": True, "description": "A note.", "rationale": "x",
    }]
    judgment["changes"] = [
        {"kind": "add_column", "column": "line_note", "before": "", "after": "VARCHAR", "rationale": "x"},
        {"kind": "required_change", "column": "line_note", "before": "false", "after": "true", "rationale": "the F-28 follow-up"},
    ]
    full = amend_proposal(committed, judgment)
    added = next(c for c in full["columns"] if c["name"] == "line_note")
    assert added["required"] is False
    assert full["proposed_version"] == "1.3.0"  # widening: minor
    fresh = profile("profiles/silver.silver_invoice_lines/v0002.json")
    found = validate_amend(full, fresh, committed, allow_relaxation=False)
    # The validator judges the addition on its own terms; the skeleton
    # never produced a required addition for it to refuse.
    assert not any("must enter required false" in e for e in found), found


def test_a_narrowing_is_refused_by_the_validator_without_the_flag() -> None:
    committed = _committed()
    judgment = amend_judgment()
    judgment["changes"] = [
        {"kind": "required_change", "column": "invoice_id", "before": "true", "after": "false", "rationale": "x"},
    ]
    full = amend_proposal(committed, judgment)
    assert full["proposed_version"] == "2.0.0"
    assert next(c for c in full["columns"] if c["name"] == "invoice_id")["required"] is False
    fresh = profile("profiles/silver.silver_invoice_lines/v0002.json")
    found = validate_amend(full, fresh, committed, allow_relaxation=False)
    assert any(e.startswith("relaxation:") for e in found), found
    assert validate_amend(full, fresh, committed, allow_relaxation=True) == [] or not any(
        e.startswith("relaxation:") for e in validate_amend(full, fresh, committed, allow_relaxation=True)
    )


def test_amend_changes_apply_as_declared_and_unknown_names_are_refused() -> None:
    committed = _committed()
    base = amend_judgment()
    base["changes"] = []
    base["added_columns"] = []
    base["grain_keys"] = []

    def with_changes(*changes: dict, added: list | None = None) -> dict:
        judgment = copy.deepcopy(base)
        judgment["changes"] = list(changes)
        judgment["added_columns"] = added or []
        return skeleton.apply_judgment(skeleton.amend_skeleton(committed), judgment)

    dropped = with_changes({"kind": "drop_column", "column": "country", "before": "VARCHAR", "after": "", "rationale": "x"})
    assert "country" not in [c["name"] for c in dropped["columns"]]
    retyped = with_changes({"kind": "retype_column", "column": "quantity", "before": "INTEGER", "after": "BIGINT", "rationale": "x"})
    quantity = next(c for c in retyped["columns"] if c["name"] == "quantity")
    assert quantity["physical_type"] == "BIGINT" and quantity["logical_type"] == "integer"
    base["grain_keys"] = []
    regrained = with_changes({"kind": "grain_change", "column": "", "before": "a,b", "after": "invoice_id, stock_code", "rationale": "x"})
    assert regrained["grain_keys"] == ["invoice_id", "stock_code"]
    base["grain_keys"] = ["invoice_id", "stock_code"]
    assert with_changes({"kind": "grain_change", "column": "", "before": "a,b", "after": "invoice_id, stock_code", "rationale": "x"})["grain_keys"] == ["invoice_id", "stock_code"]
    base["grain_keys"] = []
    # The F-28 follow-up on an addition is skipped whichever order the two
    # changes are listed in.
    reordered = with_changes(
        {"kind": "required_change", "column": "extra", "before": "false", "after": "true", "rationale": "x"},
        {"kind": "add_column", "column": "extra", "before": "", "after": "", "rationale": "x"},
        added=[{"name": "extra", "logical_type": "string", "physical_type": "VARCHAR",
                "required": False, "description": "d", "rationale": "r"}],
    )
    assert next(c for c in reordered["columns"] if c["name"] == "extra")["required"] is False
    unchanged = with_changes()
    assert unchanged["proposed_version"] == "1.2.0" and unchanged["changes"] == []
    for kind in ("drop_column", "retype_column", "required_change", "description_change"):
        with pytest.raises(SkeletonError, match=f"{kind} 'ghost' names no committed column"):
            with_changes({"kind": kind, "column": "ghost", "before": "", "after": "x", "rationale": "x"})
    with pytest.raises(SkeletonError, match="add_column 'extra' has no added_columns entry"):
        with_changes({"kind": "add_column", "column": "extra", "before": "", "after": "", "rationale": "x"})
    with pytest.raises(SkeletonError, match="names a column the committed contract already carries"):
        with_changes(
            {"kind": "add_column", "column": "country", "before": "", "after": "", "rationale": "x"},
            added=[{"name": "country", "logical_type": "string", "physical_type": "VARCHAR",
                    "required": False, "description": "d", "rationale": "r"}],
        )
    with pytest.raises(SkeletonError, match="stance 'describe' is not the run's stance 'amend'"):
        judgment = copy.deepcopy(base)
        judgment["stance"] = "describe"
        skeleton.apply_judgment(skeleton.amend_skeleton(committed), judgment)
    # The two corners the design round's re-read found: a drop then an
    # add of the same name would re-emit the machine half under a new
    # type, and two grain changes would leave the grain ambiguous. Both
    # are refused before the validator sees them, so no machine-half
    # string is reachable under arm B.
    with pytest.raises(SkeletonError, match="names a column the committed contract already carries"):
        with_changes(
            {"kind": "drop_column", "column": "quantity", "before": "INTEGER", "after": "", "rationale": "x"},
            {"kind": "add_column", "column": "quantity", "before": "", "after": "", "rationale": "x"},
            added=[{"name": "quantity", "logical_type": "integer", "physical_type": "BIGINT",
                    "required": False, "description": "d", "rationale": "r"}],
        )
    with pytest.raises(SkeletonError, match="at most one grain_change"):
        with_changes(
            {"kind": "grain_change", "column": "", "before": "a", "after": "invoice_id", "rationale": "x"},
            {"kind": "grain_change", "column": "", "before": "a", "after": "invoice_id, stock_code", "rationale": "x"},
        )


def test_the_judgment_schema_is_the_structured_outputs_subset_and_its_examples_validate() -> None:
    schema = json.loads(JUDGMENT_SCHEMA.read_text(encoding="utf-8"))
    forbidden = {"allOf", "anyOf", "oneOf", "not", "if", "then", "else", "$ref", "patternProperties", "dependentSchemas"}

    def walk(node: object, where: str) -> None:
        if isinstance(node, dict):
            assert not (set(node) & forbidden), (where, set(node) & forbidden)
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, where
                assert sorted(node.get("required", [])) == sorted(node.get("properties", {})), where
            if "enum" in node:
                assert node.get("type") == "string", where
                assert all(isinstance(v, str) for v in node["enum"]), where
            for key, child in node.items():
                walk(child, f"{where}/{key}")
        elif isinstance(node, list):
            for i, child in enumerate(node):
                walk(child, f"{where}[{i}]")

    walk(schema, "#")
    assert schema["properties"]["stance"]["enum"] == ["describe", "amend"]
    local, wire = harness.load_proposal_schema(JUDGMENT_SCHEMA)
    validator = Draft202012Validator(local)
    examples_dir = JUDGMENT_SCHEMA.parent
    for name in ("example-describe-judgment.json", "example-amend-judgment.json"):
        example = json.loads((examples_dir / name).read_text(encoding="utf-8"))
        assert list(validator.iter_errors(example)) == [], name
    assert len(json.dumps(wire, separators=(",", ":"))) < 8_000
    describe_example = json.loads((examples_dir / "example-describe-judgment.json").read_text(encoding="utf-8"))
    fresh = profile("profiles/silver.silver_invoice_lines/v0002.json")
    full = skeleton.apply_judgment(skeleton.describe_skeleton(fresh), describe_example)
    assert validate_describe(full, fresh) == []
    assert list(_proposal_validator().iter_errors(full)) == []


def test_the_judgment_schema_digest_differs_from_the_frozen_proposal_schema() -> None:
    assert e3._schema_digest(JUDGMENT_SCHEMA) != e3._schema_digest(PROPOSAL_SCHEMA)
    assert e3._schema_digest(JUDGMENT_SCHEMA).startswith("sha256:")
