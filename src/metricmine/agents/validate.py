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


# ---------------------------------------------------------------------------
# The amend stance (D-35; D-08; F-28)

# Direction classification per D-35: an amendment never weakens a
# contract; the validator classifies every change as widening, neutral,
# or narrowing, and narrowing is refused unless --allow-relaxation is
# passed (then renders at a major bump with the printed rule-6 warning).
# The unnamed retype direction and any grain change classify narrowing
# by conservative reading (S-Q-prep-5): both rewrite an enforced promise,
# and the project carries no type lattice to prove one direction safe.
_RULE_SIGNATURE_KINDS = (
    "row_count_positive",
    "grain_unique",
    "not_null",
    "non_negative",
    "accepted_values_subset",
)


def rule_signature_of_committed(entry: dict, column: str) -> str:
    """Classify one committed quality entry into a closed-list signature.

    `column` is the empty string for a table-level entry. A hand-authored
    rule outside the closed list returns `custom` and is never touched by
    the amend stance: review owns it (D-24).
    """
    if entry.get("type") == "library" and entry.get("metric") == "rowCount":
        return "row_count_positive"
    query = entry.get("query", "")
    if entry.get("type") == "sql" and not column and "GROUP BY" in query:
        return "grain_unique"
    if entry.get("type") == "sql" and column:
        if "IS NULL" in query:
            return f"not_null:{column}"
        if "< 0" in query:
            return f"non_negative:{column}"
        if "NOT IN" in query:
            return f"accepted_values_subset:{column}"
    return "custom"


def committed_rule_signatures(committed: dict) -> set[str]:
    """Every closed-list signature the committed document carries."""
    table_object = committed["schema"][0]
    signatures = {
        rule_signature_of_committed(entry, "")
        for entry in table_object.get("quality", [])
    }
    for prop in table_object.get("properties", []):
        for entry in prop.get("quality", []):
            signatures.add(rule_signature_of_committed(entry, prop["name"]))
    signatures.discard("custom")
    return signatures


def classify_change(change: dict) -> str:
    """widening | neutral | narrowing for one declared change (D-35).

    Widening strengthens the promise (add_column, an added rule,
    required false to true). Neutral moves prose only
    (description_change, no_change). Everything else narrows: a dropped
    column, required true to false, a removed or modified rule, ANY
    retype_column, ANY grain_change. The register names only the
    widened-type case; no type lattice exists here, so the conservative
    reading (S-Q-prep-5) classifies every retype and every grain change
    as narrowing and lets rule 6 hold by construction.
    """
    kind = change["kind"]
    if kind == "add_column":
        return "widening"
    if kind in ("description_change", "no_change"):
        return "neutral"
    if kind == "required_change":
        return "widening" if change["after"] == "true" else "narrowing"
    if kind == "rule_change":
        if change["before"] == "" and change["after"]:
            return "widening"
        return "narrowing"
    # drop_column, retype_column, grain_change
    return "narrowing"


def derive_bump(changes: list[dict]) -> str:
    """The version bump class the declared changes justify (D-08, F-20).

    Deterministic, never the model's proposed_version: any narrowing
    change forces major, else any widening forces minor, else patch.
    The human still sets the final version at approval (F-20).
    """
    directions = {classify_change(change) for change in changes}
    if "narrowing" in directions:
        return "major"
    if "widening" in directions:
        return "minor"
    return "patch"


def next_version(current: str | None, bump: str) -> str:
    """Semver bump; a missing committed target starts the line at 1.0.0."""
    if current is None:
        return "1.0.0"
    major, minor, patch = (int(part) for part in current.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown bump {bump!r}")


def _committed_properties(committed: dict) -> dict[str, dict]:
    return {
        prop["name"]: prop
        for prop in committed["schema"][0].get("properties", [])
    }


def _committed_grain(committed: dict) -> list[str]:
    keyed = [
        prop
        for prop in committed["schema"][0].get("properties", [])
        if prop.get("primaryKey")
    ]
    keyed.sort(key=lambda prop: prop.get("primaryKeyPosition", 0))
    return [prop["name"] for prop in keyed]


def validate_amend(
    proposal: dict,
    profile: dict,
    committed: dict,
    *,
    allow_relaxation: bool = False,
) -> list[str]:
    """Groundedness, completeness, and the direction gate for amend (D-35).

    Patch semantics: the declared changes[] list is the only channel
    through which the committed document moves, so the diff is the
    declared set by construction. This validator holds three duties:
    every declared change is TRUE against the committed document and the
    fresh profile (a false claim is refused); the re-emitted machine half
    (columns, grain, required flags, types) equals committed-plus-changes
    (an undeclared move is refused, symmetrically for drops and
    additions); and the D-08 direction gate (narrowing refused without
    --allow-relaxation). Additions enter optional; a same-column
    required_change false->true is recorded as the declared F-28
    follow-up and deferred, never applied in this amendment. Errors
    carrying the `relaxation:` prefix are the no-retry class, exactly
    like staleness: narrowing is the operator's call, never the model's
    to walk back, so the harness fails closed at once and the remedy is
    the explicit flag.
    """
    errors: list[str] = []
    dataset = profile["dataset"]
    by_name = {column["name"]: column for column in dataset["columns"]}
    committed_props = _committed_properties(committed)
    committed_grain = _committed_grain(committed)
    changes = proposal["changes"]

    if proposal["stance"] != "amend":
        errors.append(
            f"completeness: stance {proposal['stance']!r} is not amend; "
            f"this run only accepts amend proposals"
        )
        return errors
    if proposal["target_table"] != committed.get("id"):
        errors.append(
            f"groundedness: target_table {proposal['target_table']!r} is "
            f"not the committed contract id {committed.get('id')!r}"
        )
    if proposal["target_schema"] != dataset["schema"]:
        errors.append(
            f"groundedness: target_schema {proposal['target_schema']!r} is "
            f"not the profiled schema {dataset['schema']!r}"
        )
    if proposal["target_table"] != dataset["table"]:
        errors.append(
            f"groundedness: target_table {proposal['target_table']!r} is "
            f"not the profiled table {dataset['table']!r}; amend consumes "
            f"the target table's own fresh profile"
        )

    if not _SEMVER.match(proposal["proposed_version"]):
        errors.append(
            f"completeness: proposed_version "
            f"{proposal['proposed_version']!r} is not semver"
        )
    effective = [c for c in changes if c["kind"] != "no_change"]
    if not changes:
        errors.append(
            "completeness: amend requires at least one changes[] entry; "
            "changes[] is the amendment's only channel"
        )
    elif not effective:
        errors.append(
            "completeness: every declared change is no_change; there is "
            "nothing to amend, and the committed contract stands"
        )

    seen: set[tuple[str, str, str]] = set()
    added_columns: dict[str, dict] = {}
    dropped: set[str] = set()
    deferred_required: set[str] = set()
    proposal_cols = {c["name"]: c for c in proposal["columns"]}

    add_names = {c["column"] for c in changes if c["kind"] == "add_column"}

    for change in changes:
        kind = change["kind"]
        column = change["column"]
        before = change["before"]
        after = change["after"]
        key = (kind, column, before + "->" + after)
        if key in seen:
            errors.append(
                f"completeness: duplicate change {kind} on "
                f"{column or 'table'}"
            )
            continue
        seen.add(key)
        if kind in ("grain_change", "rule_change", "no_change"):
            if column:
                errors.append(
                    f"completeness: table-level change {kind} must carry "
                    f"an empty column"
                )
                continue
        elif not column:
            errors.append(
                f"completeness: column change {kind} must name a column"
            )
            continue

        if kind == "add_column":
            if column in committed_props:
                errors.append(
                    f"completeness: add_column {column!r} already exists "
                    f"in the committed contract"
                )
                continue
            entry = proposal_cols.get(column)
            if entry is None:
                errors.append(
                    f"completeness: add_column {column!r} has no matching "
                    f"columns[] entry carrying its full definition"
                )
                continue
            added_columns[column] = entry
            # A drift-add (the column already exists in the warehouse) is
            # evidence-held to the profiled type; a contract-first add
            # (F-28) is grounded by the intent and has no profile row.
            profiled = by_name.get(column)
            if profiled is not None and (
                entry["physical_type"] != profiled["physical_type"]
            ):
                errors.append(
                    f"groundedness: added column {column!r} declares "
                    f"physical_type {entry['physical_type']!r} but the "
                    f"fresh profile measures "
                    f"{profiled['physical_type']!r}"
                )
        elif kind == "drop_column":
            if column not in committed_props:
                errors.append(
                    f"completeness: drop_column {column!r} is a false "
                    f"claim; the committed contract declares no such "
                    f"column"
                )
                continue
            dropped.add(column)
            if column in proposal_cols:
                errors.append(
                    f"completeness: drop_column {column!r} still appears "
                    f"in columns[]"
                )
        elif kind == "retype_column":
            committed_prop = committed_props.get(column)
            profiled = by_name.get(column)
            if committed_prop is None:
                errors.append(
                    f"completeness: retype_column {column!r} is a false "
                    f"claim; the committed contract declares no such "
                    f"column"
                )
                continue
            if before != committed_prop.get("physicalType"):
                errors.append(
                    f"completeness: retype_column {column!r} claims "
                    f"before {before!r} but the committed physicalType is "
                    f"{committed_prop.get('physicalType')!r}"
                )
            if profiled is None:
                errors.append(
                    f"groundedness: retype_column {column!r} names no "
                    f"column of the fresh profile; a retype follows "
                    f"measured drift, never invents a type"
                )
            elif after != profiled["physical_type"]:
                errors.append(
                    f"groundedness: retype_column {column!r} proposes "
                    f"{after!r} but the fresh profile measures "
                    f"{profiled['physical_type']!r}; a retype follows the "
                    f"type the engine produced"
                )
        elif kind == "required_change":
            if before not in ("true", "false") or after not in (
                "true",
                "false",
            ):
                errors.append(
                    f"completeness: required_change {column!r} must carry "
                    f"before and after as 'true' or 'false'"
                )
                continue
            if before == after:
                errors.append(
                    f"completeness: required_change {column!r} declares "
                    f"no change"
                )
                continue
            if column in add_names:
                if after != "true":
                    errors.append(
                        f"completeness: required_change {column!r} on an "
                        f"added column only makes sense as the declared "
                        f"false->true follow-up (F-28)"
                    )
                    continue
                # The declared F-28 follow-up: recorded, never applied by
                # the patch; the addition enters optional.
                deferred_required.add(column)
                continue
            committed_prop = committed_props.get(column)
            if committed_prop is None:
                errors.append(
                    f"completeness: required_change {column!r} is a false "
                    f"claim; the committed contract declares no such "
                    f"column"
                )
                continue
            committed_required = (
                "true" if committed_prop.get("required") else "false"
            )
            if before != committed_required:
                errors.append(
                    f"completeness: required_change {column!r} claims "
                    f"before {before!r} but the committed required is "
                    f"{committed_required!r}"
                )
            profiled = by_name.get(column)
            if (
                after == "true"
                and profiled is not None
                and profiled["null_rate"] != 0.0
            ):
                errors.append(
                    f"groundedness: required_change {column!r} to true "
                    f"contradicts the fresh profile's nonzero null_rate "
                    f"{profiled['null_rate']!r}"
                )
        elif kind == "description_change":
            committed_prop = committed_props.get(column)
            if committed_prop is None:
                errors.append(
                    f"completeness: description_change {column!r} is a "
                    f"false claim; the committed contract declares no "
                    f"such column"
                )
                continue
            # `before` is the model's short quote and stays advisory: long
            # committed prose is not transcribed verbatim.
            if not after.strip():
                errors.append(
                    f"completeness: description_change {column!r} "
                    f"proposes an empty description"
                )
            elif after.strip() == str(
                committed_prop.get("description", "")
            ).strip():
                errors.append(
                    f"completeness: description_change {column!r} matches "
                    f"the committed text; nothing changes"
                )
        elif kind == "grain_change":
            committed_csv = ", ".join(committed_grain)
            if before != committed_csv:
                errors.append(
                    f"completeness: grain_change claims before {before!r} "
                    f"but the committed grain is {committed_csv!r}"
                )
            proposed_keys = [
                part.strip() for part in after.split(",") if part.strip()
            ]
            if not proposed_keys:
                errors.append(
                    "completeness: grain_change proposes an empty grain"
                )
            if proposed_keys != proposal["grain_keys"]:
                errors.append(
                    f"completeness: grain_change after {after!r} disagrees "
                    f"with grain_keys {proposal['grain_keys']}"
                )
        elif kind == "rule_change":
            for side, signature in (("before", before), ("after", after)):
                if not signature:
                    continue
                sig_kind = signature.split(":", 1)[0]
                if sig_kind not in _RULE_SIGNATURE_KINDS:
                    errors.append(
                        f"completeness: rule_change {side} {signature!r} "
                        f"is outside the closed rule list; hand-authored "
                        f"rules are review-owned and never moved by a "
                        f"stance"
                    )
            if not before and not after:
                errors.append("completeness: rule_change declares nothing")
            if before and before not in committed_rule_signatures(committed):
                errors.append(
                    f"completeness: rule_change removes {before!r} but "
                    f"the committed contract carries no such rule"
                )
            if after:
                sig_kind, _, sig_column = after.partition(":")
                matching = [
                    rule
                    for rule in proposal["quality_rules"]
                    if rule["kind"] == sig_kind
                    and rule["column"] == sig_column
                ]
                if not matching:
                    errors.append(
                        f"completeness: rule_change adds {after!r} but no "
                        f"quality_rules[] entry carries its definition"
                    )
                elif sig_column:
                    # A column-level added rule is evidence-checked exactly
                    # as the describe stance checks it.
                    profiled = by_name.get(sig_column)
                    if profiled is None:
                        errors.append(
                            f"groundedness: rule {after!r} names no "
                            f"profiled column"
                        )
                    elif (
                        sig_kind == "not_null"
                        and profiled["null_rate"] != 0.0
                    ):
                        errors.append(
                            f"groundedness: not_null on {sig_column!r} "
                            f"contradicts its nonzero profiled null_rate"
                        )
                    elif sig_kind == "non_negative":
                        minimum = profiled.get("min")
                        if not _is_number(minimum) or minimum < 0:
                            errors.append(
                                f"groundedness: non_negative on "
                                f"{sig_column!r} is unsupported by the "
                                f"profiled min {minimum!r}"
                            )

    # A recorded decision is never re-valued by a stance: the renderer
    # carries the committed decision* entries untouched, so a proposal
    # that re-keys one is refused here (changing a recorded decision is
    # a human edit in the editor, D-24).
    committed_keys = {
        entry.get("property")
        for entry in committed.get("customProperties", [])
    }
    for decision in proposal.get("decisions", []):
        if decision["key"] in committed_keys:
            errors.append(
                f"completeness: decision key {decision['key']!r} is "
                f"already recorded in the committed contract; changing a "
                f"recorded decision is a human edit, never a stance's "
                f"re-valuation"
            )

    # The undeclared-move guard, symmetric (the stance probe's rule).
    for name in committed_props:
        if name not in proposal_cols and name not in dropped:
            errors.append(
                f"completeness: committed column {name!r} is missing from "
                f"columns[] with no declared drop_column (an undeclared "
                f"drop)"
            )
    declared = {(c["kind"], c["column"]) for c in changes}
    for name, entry in proposal_cols.items():
        committed_prop = committed_props.get(name)
        if committed_prop is None:
            if name not in added_columns:
                errors.append(
                    f"completeness: column {name!r} is new with no "
                    f"declared add_column (an undeclared addition)"
                )
            elif entry["required"]:
                errors.append(
                    f"completeness: added column {name!r} must enter "
                    f"required false; additions tighten in a follow-up "
                    f"amendment after the model lands (F-28)"
                )
            continue
        if entry["physical_type"] != committed_prop.get("physicalType") and (
            "retype_column",
            name,
        ) not in declared:
            errors.append(
                f"completeness: {name!r} re-emits physical_type "
                f"{entry['physical_type']!r} against the committed "
                f"{committed_prop.get('physicalType')!r} with no declared "
                f"retype_column (an undeclared move)"
            )
        committed_required = bool(committed_prop.get("required"))
        if entry["required"] != committed_required and (
            "required_change",
            name,
        ) not in declared:
            errors.append(
                f"completeness: {name!r} re-emits required "
                f"{entry['required']!r} against the committed "
                f"{committed_required!r} with no declared required_change "
                f"(an undeclared move)"
            )

    grain_declared = any(c["kind"] == "grain_change" for c in changes)
    if proposal["grain_keys"] != committed_grain and not grain_declared:
        errors.append(
            f"completeness: grain_keys {proposal['grain_keys']} disagree "
            f"with the committed grain {committed_grain} with no declared "
            f"grain_change (an undeclared move)"
        )

    # The bump class is derived, never trusted (D-08, F-20): the human
    # still sets the final version at approval, but the PROPOSED version
    # must be the committed version bumped by the worst declared
    # direction, so the terminal line and the draft agree by
    # construction.
    if changes and _SEMVER.match(proposal["proposed_version"]):
        expected_version = next_version(
            str(committed.get("version")), derive_bump(changes)
        )
        if proposal["proposed_version"] != expected_version:
            errors.append(
                f"completeness: proposed_version "
                f"{proposal['proposed_version']!r} must be "
                f"{expected_version!r}: the committed "
                f"{committed.get('version')!r} bumped "
                f"{derive_bump(changes)!r} by the declared change "
                f"directions (D-08, F-20)"
            )

    # The D-08 direction gate: it fires over a claim-true change set (a
    # version arithmetic slip does not mask it), so the operator reads
    # real narrowing, not a false claim.
    claim_errors = [e for e in errors if "proposed_version" not in e]
    if not claim_errors and not allow_relaxation:
        narrowing = [
            f"{c['kind']} {c['column'] or 'table'}"
            for c in changes
            if classify_change(c) == "narrowing"
        ]
        if narrowing:
            errors.append(
                "relaxation: this amendment NARROWS the contract "
                f"({'; '.join(narrowing)}); narrowing is refused without "
                "--allow-relaxation (make propose-amend ... "
                "ALLOW_RELAXATION=1), renders at a MAJOR version bump, "
                "and prints the rule-6 warning (D-35, D-08)"
            )
    return errors
