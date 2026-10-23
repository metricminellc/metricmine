"""E3b, the skeleton: code writes the machine half, the model declares the
judgment over it (experiment branch only; docs/experiments/e3/KEY.md).

For the describe stance the machine half comes from the profile artifact:
every profiled column once, in profile order, the profiled physical type,
`required` equal to (null_rate == 0.0), the logical type from the
validator's own fixed map, and the two fixed table rules. For the amend
stance it comes from the committed contract: its columns as they stand,
its grain, and the proposed version derived from the declared changes.
The model emits a judgment object (docs/spec/agent-layer/e3/
table-contract-judgment.schema.json); `apply_judgment` builds the full
proposal the unchanged validator then judges, so every gate still holds
and a draft reaches the outbox the same way. Nothing here calls a model,
reads the warehouse, or writes a file.
"""

from __future__ import annotations

import copy

from metricmine.agents.harness import SkeletonError
from metricmine.agents.validate import _expected_logical, derive_bump, next_version

FIXED_RULE_RATIONALE = "A fixed table rule, written by code (E3b): every described table carries it."


def describe_skeleton(artifact: dict) -> dict:
    """The machine half of a describe proposal from the profile alone."""
    dataset = artifact["dataset"]
    columns = [
        {
            "name": column["name"],
            "logical_type": _expected_logical(column["physical_type"]) or "string",
            "physical_type": column["physical_type"],
            "required": column["null_rate"] == 0.0,
            "description": "",
            "rationale": "",
        }
        for column in dataset["columns"]
    ]
    return {
        "stance": "describe",
        "target_schema": dataset["schema"],
        "target_table": dataset["table"],
        "proposed_version": "1.0.0",
        "columns": columns,
        "grain_keys": [],
        "quality_rules": [
            {"kind": "row_count_positive", "column": "", "values": [], "rationale": FIXED_RULE_RATIONALE},
            {"kind": "grain_unique", "column": "", "values": [], "rationale": FIXED_RULE_RATIONALE},
        ],
        "changes": [],
        "decisions": [],
        "purpose": "",
        "usage": "",
        "limitations": "",
    }


def amend_skeleton(committed: dict) -> dict:
    """The machine half of an amend proposal: the committed contract as it
    stands. `proposed_version` is derived once the changes are known."""
    table_object = committed["schema"][0]
    properties = table_object.get("properties", [])
    keyed = sorted(
        (prop for prop in properties if prop.get("primaryKey")),
        key=lambda prop: prop.get("primaryKeyPosition", 0),
    )
    description = committed.get("description") or {}
    return {
        "stance": "amend",
        "target_schema": _server_schema(committed),
        "target_table": committed["id"],
        "proposed_version": str(committed["version"]),
        "columns": [
            {
                "name": prop["name"],
                "logical_type": prop["logicalType"],
                "physical_type": prop["physicalType"],
                "required": bool(prop.get("required")),
                "description": str(prop.get("description", "")).strip(),
                "rationale": "Carried from the committed contract by code (E3b).",
            }
            for prop in properties
        ],
        "grain_keys": [prop["name"] for prop in keyed],
        "quality_rules": [],
        "changes": [],
        "decisions": [],
        "purpose": str(description.get("purpose", "")),
        "usage": str(description.get("usage", "")),
        "limitations": str(description.get("limitations", "")),
    }


def _server_schema(committed: dict) -> str:
    servers = committed.get("servers") or []
    return servers[0].get("schema", "silver") if servers else "silver"


def apply_judgment(skeleton: dict, judgment: dict) -> dict:
    """The full proposal: the skeleton with the judgment applied over it.

    Describe: column prose by name onto the skeleton's columns, the grain,
    the column-level rules beside the two fixed rules, the decisions, the
    three prose fields. Amend: the declared changes applied to the
    skeleton's columns and grain (an added column from `added_columns`,
    entering optional; a drop removed; a retype's physical type and the
    mapped logical type; a required flag; a description), the rules a
    rule_change names, and the version derived from the declared
    directions. A judgment that names a column the skeleton does not
    carry, that describes a column twice or leaves one undescribed under
    describe, or that carries column_prose under amend raises
    SkeletonError, which the harness records as a judgment error and
    feeds back.
    """
    proposal = copy.deepcopy(skeleton)
    stance = proposal["stance"]
    if judgment["stance"] != stance:
        raise SkeletonError(
            f"the judgment's stance {judgment['stance']!r} is not the run's "
            f"stance {stance!r}"
        )
    by_name = {column["name"]: column for column in proposal["columns"]}

    if stance == "amend" and judgment["column_prose"]:
        # A description moves only by a declared description_change;
        # prose on an existing column would be applied here and then
        # ignored by the renderer, a silent no-op the prompt forbids.
        raise SkeletonError(
            "amend carries no column_prose; a description moves only by a "
            "declared description_change"
        )
    seen: set[str] = set()
    for prose in judgment["column_prose"]:
        column = by_name.get(prose["name"])
        if column is None:
            raise SkeletonError(
                f"column_prose names {prose['name']!r}, which the skeleton "
                f"does not carry; the machine half is written by code and "
                f"a judgment only describes it"
            )
        if prose["name"] in seen:
            raise SkeletonError(
                f"column_prose names {prose['name']!r} twice; every column "
                f"is described exactly once"
            )
        seen.add(prose["name"])
        column["description"] = prose["description"]
        column["rationale"] = prose["rationale"]

    if stance == "describe":
        if judgment["added_columns"] or judgment["changes"]:
            raise SkeletonError(
                "describe carries no added_columns and no changes; those "
                "are the amend stance's channels"
            )
        missing = [name for name in by_name if name not in seen]
        if missing:
            raise SkeletonError(
                f"column_prose leaves {len(missing)} profiled column(s) "
                f"undescribed: {missing}; every column is described exactly once"
            )
        proposal["grain_keys"] = list(judgment["grain_keys"])
        proposal["quality_rules"] = proposal["quality_rules"] + [
            dict(rule) for rule in judgment["quality_rules"]
        ]
    else:
        added = {entry["name"]: entry for entry in judgment["added_columns"]}
        committed_names = set(by_name)
        grain_changes = 0
        for change in judgment["changes"]:
            kind = change["kind"]
            column = change["column"]
            if kind == "add_column":
                entry = added.get(column)
                if entry is None:
                    raise SkeletonError(
                        f"add_column {column!r} has no added_columns entry "
                        f"carrying its definition"
                    )
                if column in by_name or column in committed_names:
                    # A committed name is never re-added, dropped or not:
                    # a drop then an add of the same name would re-emit
                    # the machine half under a new type.
                    raise SkeletonError(
                        f"add_column {column!r} names a column the committed "
                        f"contract already carries"
                    )
                new_column = {
                    "name": entry["name"],
                    "logical_type": entry["logical_type"],
                    "physical_type": entry["physical_type"],
                    # Additions enter optional (F-28); the declared
                    # follow-up is a later amendment.
                    "required": False,
                    "description": entry["description"],
                    "rationale": entry["rationale"],
                }
                proposal["columns"].append(new_column)
                by_name[column] = new_column
            elif kind == "drop_column":
                if column not in by_name:
                    raise SkeletonError(
                        f"drop_column {column!r} names no committed column"
                    )
                proposal["columns"] = [
                    c for c in proposal["columns"] if c["name"] != column
                ]
                del by_name[column]
            elif kind == "retype_column":
                if column not in by_name:
                    raise SkeletonError(
                        f"retype_column {column!r} names no committed column"
                    )
                by_name[column]["physical_type"] = change["after"]
                by_name[column]["logical_type"] = (
                    _expected_logical(change["after"]) or "string"
                )
            elif kind == "required_change":
                if column in added:
                    # The declared F-28 follow-up on an addition, never
                    # applied, whichever order the two changes are listed in.
                    continue
                if column not in by_name:
                    raise SkeletonError(
                        f"required_change {column!r} names no committed column"
                    )
                by_name[column]["required"] = change["after"] == "true"
            elif kind == "description_change":
                if column not in by_name:
                    raise SkeletonError(
                        f"description_change {column!r} names no committed "
                        f"column"
                    )
                by_name[column]["description"] = change["after"]
            elif kind == "grain_change":
                grain_changes += 1
                if grain_changes > 1:
                    raise SkeletonError(
                        "a judgment declares at most one grain_change; two "
                        "would leave grain_keys ambiguous"
                    )
                proposal["grain_keys"] = [
                    part.strip() for part in change["after"].split(",") if part.strip()
                ]
            # rule_change and no_change move nothing on the columns; a
            # rule_change's added rule travels in quality_rules below.
        if judgment["grain_keys"] and list(judgment["grain_keys"]) != proposal["grain_keys"]:
            # The grain moves only by a declared grain_change; a stated
            # grain_keys is checked against the committed grain plus that
            # change, never applied on its own.
            raise SkeletonError(
                f"grain_keys {list(judgment['grain_keys'])} disagrees with the "
                f"committed grain plus the declared changes {proposal['grain_keys']}; "
                f"the grain moves only by a declared grain_change"
            )
        proposal["quality_rules"] = [dict(rule) for rule in judgment["quality_rules"]]
        proposal["changes"] = [dict(change) for change in judgment["changes"]]
        if judgment["changes"]:
            proposal["proposed_version"] = next_version(
                skeleton["proposed_version"], derive_bump(judgment["changes"])
            )

    proposal["decisions"] = [dict(decision) for decision in judgment["decisions"]]
    for field in ("purpose", "usage", "limitations"):
        if judgment[field]:
            proposal[field] = judgment[field]
    return proposal


def machine_half_chars(proposal: dict) -> tuple[int, int]:
    """The compact-JSON character count of the machine half (the four
    header fields and the four machine fields of every column) and of the
    whole proposal: the September 17 reading's method."""
    import json

    machine = len(
        json.dumps(
            {k: proposal[k] for k in ("stance", "target_schema", "target_table", "proposed_version")},
            separators=(",", ":"),
        )
    ) + len(
        json.dumps(
            [
                {k: c[k] for k in ("name", "logical_type", "physical_type", "required")}
                for c in proposal["columns"]
            ],
            separators=(",", ":"),
        )
    )
    return machine, len(json.dumps(proposal, separators=(",", ":")))
