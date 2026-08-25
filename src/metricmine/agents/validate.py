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
