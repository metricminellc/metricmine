"""The deterministic proposal validator (D-23 as amended by Amendment H).

Spec: docs/spec/agent-layer.md §3. Pure functions over a parsed proposal
and its profile artifact, each returning a list of error strings (empty
means pass). Groundedness is enforced to zero, not measured: every column
a proposal references must exist in the profile. Completeness holds the
flattened proposal variants (F-26) to the consistency the frozen schemas
express with composition keywords. Staleness re-binds a proposal to the
exact artifact bytes it consumed via the profiler's content_hash
(docs/spec/profiler.md §3).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from metricmine.profiling import canonical

_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")
_RESERVED_PREFIXES = ("dim_", "fact_", "vw_", "mart_", "silver_", "bronze_", "stg_")


def _profile_columns(profile: dict) -> set[str]:
    return {column["name"] for column in profile["dataset"]["columns"]}


def validate_mapping(proposal: dict, profile: dict) -> list[str]:
    """Groundedness and completeness for a gold mapping proposal."""
    errors: list[str] = []
    columns = _profile_columns(profile)
    dataset = profile["dataset"]

    def grounded(name: str, where: str) -> None:
        if name not in columns:
            errors.append(
                f"groundedness: {where} {name!r} is not a column of the "
                f"profiled table"
            )

    for field in proposal["fields"]:
        grounded(field["name"], "field")
    grounded(proposal["time_column"], "time_column")
    for identifier in proposal["degenerate_identifiers"]:
        for entry in identifier["of"]:
            grounded(entry, "degenerate identifier column")
        if identifier["source"] == "column":
            grounded(identifier["name"], "column-source identifier")
    for aggregation in proposal["aggregations"]:
        grounded(aggregation["field"], "aggregated field")

    expected_source = f"{dataset['schema']}.{dataset['table']}"
    if proposal["source_table"] != expected_source:
        errors.append(
            f"groundedness: source_table {proposal['source_table']!r} is not "
            f"the profiled relation {expected_source!r}"
        )

    time_fields = [
        f["name"] for f in proposal["fields"] if f["mapping_role"] == "time"
    ]
    if len(time_fields) != 1:
        errors.append(
            f"completeness: exactly one field must carry mapping_role time; "
            f"got {time_fields or 'none'}"
        )
    elif time_fields[0] != proposal["time_column"]:
        errors.append(
            f"completeness: the time field {time_fields[0]!r} must equal "
            f"time_column {proposal['time_column']!r}"
        )

    grain = proposal["grain_type"]
    identifiers = proposal["degenerate_identifiers"]
    aggregations = proposal["aggregations"]
    if grain == "transaction":
        if not identifiers:
            errors.append(
                "completeness: transaction grain requires at least one "
                "degenerate identifier"
            )
        if aggregations:
            errors.append(
                "completeness: transaction grain must carry no aggregations"
            )
    else:  # aggregated
        if not aggregations:
            errors.append(
                "completeness: aggregated grain requires at least one "
                "aggregation"
            )
        if identifiers:
            errors.append(
                "completeness: aggregated grain must carry no degenerate "
                "identifiers"
            )
        roles = {f["name"]: f["mapping_role"] for f in proposal["fields"]}
        for aggregation in aggregations:
            if roles.get(aggregation["field"]) != "measure":
                errors.append(
                    f"completeness: aggregated field {aggregation['field']!r} "
                    f"must carry mapping_role measure"
                )
    for identifier in identifiers:
        if identifier["source"] == "derived" and not identifier["of"]:
            errors.append(
                f"completeness: derived identifier {identifier['name']!r} "
                f"requires a non-empty 'of' list"
            )
        if identifier["source"] == "column" and identifier["of"]:
            errors.append(
                f"completeness: column identifier {identifier['name']!r} "
                f"must carry an empty 'of' list"
            )

    category = proposal["category_name"]
    if category.startswith(_RESERVED_PREFIXES) or category == "context_registry":
        errors.append(
            f"completeness: category_name {category!r} collides with the "
            f"reserved model-name space (engine spec naming rule, F-12)"
        )

    names = [f["name"] for f in proposal["fields"]]
    if len(names) != len(set(names)):
        errors.append("completeness: field names must be unique")

    return errors


def validate_cleanup(proposal: dict, profile: dict) -> list[str]:
    """Groundedness and completeness for a silver cleanup proposal."""
    errors: list[str] = []
    columns = _profile_columns(profile)

    for column in proposal["columns"]:
        if column["source_column"] not in columns:
            errors.append(
                f"groundedness: source_column {column['source_column']!r} is "
                f"not a column of the profiled table"
            )

    if not proposal["target_table"].startswith("silver_"):
        errors.append(
            f"completeness: target_table {proposal['target_table']!r} must "
            f"start with silver_"
        )

    kept = [c for c in proposal["columns"] if c["action"] != "drop"]
    targets = [c["target_name"] for c in kept]
    if len(targets) != len(set(targets)):
        errors.append("completeness: non-drop target names must be unique")
    for name in targets:
        if not _SNAKE_CASE.match(name):
            errors.append(
                f"completeness: target name {name!r} is not snake_case"
            )
    for column in proposal["columns"]:
        if column["action"] == "drop" and column["target_name"]:
            errors.append(
                f"completeness: drop of {column['source_column']!r} must "
                f"carry an empty target_name"
            )

    if not proposal["grain_keys"]:
        errors.append("completeness: at least one grain key is required")
    required = {c["target_name"] for c in kept if c["required"]}
    target_set = set(targets)
    for key_list, label in (
        (proposal["grain_keys"], "grain key"),
        (proposal["dedupe_keys"], "dedupe key"),
    ):
        for key in key_list:
            if key not in target_set:
                errors.append(
                    f"completeness: {label} {key!r} names no non-drop target "
                    f"column"
                )
    for key in proposal["grain_keys"]:
        if key in target_set and key not in required:
            errors.append(
                f"completeness: grain key {key!r} must be required true"
            )

    dropped = {
        c["source_column"] for c in proposal["columns"] if c["action"] == "drop"
    }
    for column in profile["dataset"]["columns"]:
        if column.get("is_airbyte_metadata") and column["name"] not in dropped:
            errors.append(
                f"completeness: airbyte metadata column {column['name']!r} "
                f"must be proposed with action drop"
            )

    return errors


_LOGICAL_FROM_PHYSICAL = (
    (("VARCHAR", "JSON"), "string"),
    (("INTEGER", "BIGINT", "SMALLINT", "HUGEINT"), "integer"),
    (("DECIMAL", "DOUBLE", "FLOAT"), "number"),
    (("BOOLEAN",), "boolean"),
    (("DATE", "TIMESTAMP"), "date"),
)

# The wire schema cannot carry `pattern` (F-26), so the validator holds
# semver here.
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

_TABLE_LEVEL_RULE_KINDS = ("row_count_positive", "grain_unique")


def _expected_logical(physical_type: str) -> str | None:
    """The fixed physical-to-logical map, on the upper-cased prefix; an
    unmapped physical type returns None and is not checked."""
    upper = physical_type.upper()
    for prefixes, logical in _LOGICAL_FROM_PHYSICAL:
        if upper.startswith(prefixes):
            return logical
    return None


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_describe(proposal: dict, profile: dict) -> list[str]:
    """Groundedness and completeness for a describe proposal (D-35).

    Describe adopts an existing table AS IT IS, so the machine half is
    held to the profile exactly (D-23 as amended by Amendment H: the
    profile is the sole evidence context): every profiled column
    enumerated once in profile order, `physical_type` equal to the
    profiled type, `required` equal to (null_rate == 0.0). The judgment
    half (grain choice, descriptions, decisions, rule selection from the
    closed enum) is the model's, gated here only for evidence support.
    Grain stays unverified until `make verify-grain` measures it against
    the warehouse (F-10).
    """
    errors: list[str] = []
    dataset = profile["dataset"]
    profile_cols = dataset["columns"]
    profile_names = [column["name"] for column in profile_cols]
    by_name = {column["name"]: column for column in profile_cols}

    if proposal["stance"] != "describe":
        errors.append(
            f"completeness: stance {proposal['stance']!r} is not describe; "
            f"this run only accepts describe proposals"
        )
    if proposal["changes"]:
        errors.append(
            "completeness: describe must carry an empty changes list "
            "(changes[] is the amend stance's channel)"
        )
    if proposal["target_schema"] != dataset["schema"]:
        errors.append(
            f"groundedness: target_schema {proposal['target_schema']!r} is "
            f"not the profiled schema {dataset['schema']!r}"
        )
    if proposal["target_table"] != dataset["table"]:
        errors.append(
            f"groundedness: target_table {proposal['target_table']!r} is "
            f"not the profiled table {dataset['table']!r}"
        )
    if not _SEMVER.match(proposal["proposed_version"]):
        errors.append(
            f"completeness: proposed_version "
            f"{proposal['proposed_version']!r} is not semver"
        )

    proposed_names = [column["name"] for column in proposal["columns"]]
    if proposed_names != profile_names:
        errors.append(
            f"completeness: columns must enumerate the profiled columns in "
            f"profile order; expected {profile_names}, got {proposed_names}"
        )
    for column in proposal["columns"]:
        profiled = by_name.get(column["name"])
        if profiled is None:
            errors.append(
                f"groundedness: column {column['name']!r} is not a column "
                f"of the profiled table"
            )
            continue
        if column["physical_type"] != profiled["physical_type"]:
            errors.append(
                f"groundedness: {column['name']}.physical_type "
                f"{column['physical_type']!r} disagrees with the profiled "
                f"{profiled['physical_type']!r}; describe enforces the "
                f"type the engine produced"
            )
        evidence_required = profiled["null_rate"] == 0.0
        if column["required"] != evidence_required:
            errors.append(
                f"groundedness: {column['name']}.required "
                f"{column['required']!r} disagrees with the profiled "
                f"null_rate {profiled['null_rate']!r}"
            )
        expected = _expected_logical(column["physical_type"])
        if expected is not None and column["logical_type"] != expected:
            errors.append(
                f"completeness: {column['name']}.logical_type "
                f"{column['logical_type']!r} must be {expected!r} for "
                f"physical type {column['physical_type']!r}"
            )

    if not proposal["grain_keys"]:
        errors.append("completeness: at least one grain key is required")
    for key in proposal["grain_keys"]:
        if key not in by_name:
            errors.append(
                f"groundedness: grain key {key!r} names no profiled column"
            )
        elif by_name[key]["null_rate"] != 0.0:
            errors.append(
                f"completeness: grain key {key!r} has a nonzero profiled "
                f"null_rate and cannot identify a row"
            )

    kinds = [rule["kind"] for rule in proposal["quality_rules"]]
    if kinds.count("row_count_positive") != 1:
        errors.append(
            "completeness: exactly one row_count_positive rule is required"
        )
    if kinds.count("grain_unique") != 1:
        errors.append("completeness: exactly one grain_unique rule is required")
    for rule in proposal["quality_rules"]:
        kind = rule["kind"]
        if kind in _TABLE_LEVEL_RULE_KINDS:
            if rule["column"]:
                errors.append(
                    f"completeness: table-level rule {kind} must carry an "
                    f"empty column"
                )
        else:
            profiled = by_name.get(rule["column"])
            if profiled is None:
                errors.append(
                    f"groundedness: rule {kind} names unknown column "
                    f"{rule['column']!r}"
                )
                continue
            if kind == "not_null" and profiled["null_rate"] != 0.0:
                errors.append(
                    f"groundedness: not_null on {rule['column']!r} "
                    f"contradicts its nonzero profiled null_rate"
                )
            if kind == "non_negative":
                minimum = profiled.get("min")
                if not _is_number(minimum) or minimum < 0:
                    errors.append(
                        f"groundedness: non_negative on {rule['column']!r} "
                        f"is unsupported by the profiled min {minimum!r}"
                    )
            if kind == "accepted_values_subset":
                listed = profiled.get("distinct_values")
                if not rule["values"]:
                    errors.append(
                        f"completeness: accepted_values_subset on "
                        f"{rule['column']!r} lists no values"
                    )
                elif listed is None:
                    errors.append(
                        f"groundedness: accepted_values_subset on "
                        f"{rule['column']!r} is unsupported; the profile "
                        f"carries no full distinct_values list"
                    )
                else:
                    ghost = sorted(
                        set(rule["values"]) - {str(v) for v in listed}
                    )
                    if ghost:
                        errors.append(
                            f"groundedness: accepted_values_subset on "
                            f"{rule['column']!r} lists values absent from "
                            f"the profiled distinct_values: {ghost}"
                        )
        if kind != "accepted_values_subset" and rule["values"]:
            errors.append(
                f"completeness: rule {kind} carries values but does not "
                f"use them"
            )
    return errors


def check_staleness(profile_path: Path, bound_hash: str) -> list[str]:
    """Re-read and re-hash the artifact the proposal is bound to (D-23)."""
    try:
        artifact = json.loads(profile_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"staleness: cannot re-read {profile_path}: {exc}"]
    current = canonical.content_hash(artifact["dataset"])
    stored = artifact.get("content_hash")
    if current != stored:
        return [
            f"staleness: {profile_path} content_hash {stored} disagrees with "
            f"its recomputed dataset hash {current}"
        ]
    if current != bound_hash:
        return [
            f"staleness: {profile_path} moved to {current} after the proposal "
            f"bound to {bound_hash}"
        ]
    return []
