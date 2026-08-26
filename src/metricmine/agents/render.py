"""Proposal JSON to canonical ODCS YAML, deterministically (D-21, D-24).

Spec: docs/spec/agent-layer.md §1 (the serialization boundary: judgment
proposes, code serializes) and F-26 (the proposer emits a flat proposal;
this module renders the ODCS document the frozen schema validates). Key
order mirrors the committed render targets
(contracts/gold_invoice_lines_mapping.odcs.yaml and
contracts/silver_invoice_lines.odcs.yaml); rendering the same inputs
twice produces identical bytes. Quality-rule descriptions are STABLE
PROSE fixed here, never proposal rationale text, because datacontract
dbt sync names generated test files from them (F-27, measured
August 22, 2026). Provenance customProperties follow Appendix B order
(D-22 as amended by Amendment I: the extras hook carries later stance
and amendment keys without a renderer rewrite).
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from typing import Mapping

import yaml

from metricmine.agents.validate import (
    derive_bump,
    next_version,
    rule_signature_of_committed,
)

# Mirrors both committed contracts; the vanilla scope is one product.
API_VERSION = "v3.1.0"
DOMAIN = "retail"
DATA_PRODUCT = "metricmine"
TENANT = "metricmine"
WAREHOUSE_DB = "warehouse/metricmine.duckdb"

# Stable rule prose (F-27): sync names generated test files from these.
ROW_COUNT_RULE_DESCRIPTION = "The table is never empty"


def grain_rule_description(grain_keys: list[str]) -> str:
    return (
        f"Grain enforcement: no duplicate ({', '.join(grain_keys)}) "
        f"combinations"
    )


def not_null_rule_description(column: str) -> str:
    return f"{column} is never null"


def non_negative_rule_description(column: str) -> str:
    return f"{column} is never negative"


def accepted_values_rule_description(column: str) -> str:
    return f"{column} stays inside the accepted value set"


@dataclass(frozen=True)
class Provenance:
    """Appendix B stamp; extras is HOOK 3 (empty today, ordered, verbatim)."""

    proposed_by: str
    proposer_version: str
    prompt_version: str
    model_id: str
    profile_hash: str
    proposed_at: str  # date, YYYY-MM-DD
    extras: Mapping[str, str] = field(default_factory=dict)


def _custom_properties(provenance: Provenance, decisions: list[dict]) -> list[dict]:
    entries = [
        {"property": "proposedBy", "value": provenance.proposed_by},
        {"property": "proposerVersion", "value": provenance.proposer_version},
        {"property": "promptVersion", "value": provenance.prompt_version},
        {"property": "modelId", "value": provenance.model_id},
        {"property": "profileHash", "value": provenance.profile_hash},
        {"property": "proposedAt", "value": provenance.proposed_at},
    ]
    for key, value in provenance.extras.items():
        entries.append({"property": key, "value": value})
    for decision in decisions:
        entries.append(
            {"property": decision["key"], "value": decision["value"]}
        )
    return entries


def _grain_block(proposal: dict) -> dict:
    if proposal["grain_type"] == "transaction":
        identifiers = []
        for entry in proposal["degenerate_identifiers"]:
            identifier: dict = {"source": entry["source"], "name": entry["name"]}
            if entry["source"] == "derived":
                identifier["derivation"] = "canonical-key-v2"
                identifier["of"] = list(entry["of"])
            identifiers.append(identifier)
        return {"type": "transaction", "degenerateIdentifiers": identifiers}
    return {
        "type": "aggregated",
        "aggregations": {
            a["field"]: a["function"] for a in proposal["aggregations"]
        },
    }


def render_mapping(proposal: dict, provenance: Provenance, version: str) -> dict:
    """Insertion-ordered ODCS mapping document (mirrors the committed v1.1.0)."""
    category = proposal["category_name"]
    return {
        "apiVersion": API_VERSION,
        "kind": "DataContract",
        "id": f"gold_{category}_mapping",
        "name": f"Gold mapping, {category} category",
        "version": version,
        "status": "draft",
        "domain": DOMAIN,
        "dataProduct": DATA_PRODUCT,
        "tenant": TENANT,
        "description": {
            "purpose": proposal["purpose"],
            "usage": proposal["usage"],
            "limitations": proposal["limitations"],
        },
        "schema": [
            {
                "name": category,
                "logicalType": "object",
                "physicalType": "mapping",
                "description": proposal["category_description"],
                "entityGroup": proposal["entity_group"],
                "sourceTable": proposal["source_table"],
                "timeColumn": proposal["time_column"],
                "timeGrain": proposal["time_grain"],
                "grain": _grain_block(proposal),
                "properties": [
                    {
                        "name": f["name"],
                        "logicalType": f["logical_type"],
                        "physicalType": f["physical_type"],
                        "required": f["required"],
                        "mappingRole": f["mapping_role"],
                        "description": f["description"],
                    }
                    for f in proposal["fields"]
                ],
            }
        ],
        "servers": [
            {
                "server": "local",
                "type": "duckdb",
                "database": WAREHOUSE_DB,
                "schema": "gold",
            }
        ],
        "customProperties": _custom_properties(
            provenance, proposal.get("decisions", [])
        ),
    }


def render_cleanup(proposal: dict, provenance: Provenance, version: str) -> dict:
    """Insertion-ordered ODCS silver document (mirrors the committed v1.1.0)."""
    target = proposal["target_table"]
    kept = [c for c in proposal["columns"] if c["action"] != "drop"]
    grain_keys = proposal["grain_keys"]
    key_positions = {key: i + 1 for i, key in enumerate(grain_keys)}
    properties = []
    for column in kept:
        prop: dict = {
            "name": column["target_name"],
            "logicalType": column["logical_type"],
            "physicalType": column["physical_type"],
            "required": column["required"],
        }
        if column["target_name"] in key_positions:
            prop["primaryKey"] = True
            prop["primaryKeyPosition"] = key_positions[column["target_name"]]
        prop["description"] = column["rationale"]
        properties.append(prop)
    key_csv = ", ".join(grain_keys)
    grain_query = (
        "SELECT COUNT(*) FROM (\n"
        f"  SELECT {key_csv}\n"
        f"  FROM silver.{target}\n"
        f"  GROUP BY {key_csv}\n"
        "  HAVING COUNT(*) > 1\n"
        ")\n"
    )
    return {
        "apiVersion": API_VERSION,
        "kind": "DataContract",
        "id": target,
        "name": "Silver " + target.removeprefix("silver_").replace("_", " "),
        "version": version,
        "status": "draft",
        "domain": DOMAIN,
        "dataProduct": DATA_PRODUCT,
        "tenant": TENANT,
        "description": {
            "purpose": proposal["purpose"],
            "usage": proposal["usage"],
            "limitations": proposal["limitations"],
        },
        "schema": [
            {
                "name": target,
                "physicalName": target,
                "logicalType": "object",
                "physicalType": "table",
                "description": proposal["purpose"],
                "properties": properties,
                "quality": [
                    {
                        "type": "library",
                        "metric": "rowCount",
                        "description": ROW_COUNT_RULE_DESCRIPTION,
                        "severity": "error",
                        "mustBeGreaterThan": 0,
                    },
                    {
                        "type": "sql",
                        "description": grain_rule_description(grain_keys),
                        "severity": "error",
                        "query": grain_query,
                        "mustBe": 0,
                    },
                ],
            }
        ],
        "servers": [
            {
                "server": "local",
                "type": "duckdb",
                "database": WAREHOUSE_DB,
                "schema": "silver",
            }
        ],
        "customProperties": _custom_properties(
            provenance, proposal.get("decisions", [])
        ),
    }


_TABLE_LEVEL_RULE_KINDS = ("row_count_positive", "grain_unique")


def _describe_rule(
    rule: dict, schema: str, table: str, grain_keys: list[str]
) -> dict:
    """One closed-enum proposal rule to one ODCS quality entry.

    Descriptions are the STABLE PROSE constants above, never the
    proposal's rationale text: `datacontract dbt sync` names generated
    test files from rule descriptions (F-27), so evidence sentences stay
    in the proposal record. Severities are fixed here at error, the
    value the committed contracts established (D-35: no stance emits
    severities).
    """
    kind = rule["kind"]
    if kind == "row_count_positive":
        return {
            "type": "library",
            "metric": "rowCount",
            "description": ROW_COUNT_RULE_DESCRIPTION,
            "severity": "error",
            "mustBeGreaterThan": 0,
        }
    if kind == "grain_unique":
        key_csv = ", ".join(grain_keys)
        return {
            "type": "sql",
            "description": grain_rule_description(grain_keys),
            "severity": "error",
            "query": (
                "SELECT COUNT(*) FROM (\n"
                f"  SELECT {key_csv}\n"
                f"  FROM {schema}.{table}\n"
                f"  GROUP BY {key_csv}\n"
                "  HAVING COUNT(*) > 1\n"
                ")\n"
            ),
            "mustBe": 0,
        }
    column = rule["column"]
    if kind == "not_null":
        description = not_null_rule_description(column)
        query = (
            f"SELECT COUNT(*) FROM {schema}.{table} "
            f"WHERE {column} IS NULL\n"
        )
    elif kind == "non_negative":
        description = non_negative_rule_description(column)
        query = f"SELECT COUNT(*) FROM {schema}.{table} WHERE {column} < 0\n"
    else:  # accepted_values_subset; the schema enum admits nothing else
        description = accepted_values_rule_description(column)
        listed = ", ".join(
            "'" + value.replace("'", "''") + "'" for value in rule["values"]
        )
        query = (
            f"SELECT COUNT(*) FROM {schema}.{table} "
            f"WHERE {column} NOT IN ({listed})\n"
        )
    return {
        "type": "sql",
        "description": description,
        "severity": "error",
        "query": query,
        "mustBe": 0,
    }


def render_describe(proposal: dict, provenance: Provenance, version: str) -> dict:
    """Insertion-ordered ODCS table document for the describe stance.

    Mirrors the committed hand-written table contract
    (contracts/silver_invoice_lines.odcs.yaml) in key order, grain
    encoding (primaryKey positions plus the error-severity enforcing
    rule), and provenance order, so the describe draft and a committed
    contract diff element for element. The version comes from the
    harness parameter (a described table starts its own line at 1.0.0
    through the existing new-id rule; a regeneration under --oracle
    bumps the committed line); this renderer never reads
    proposal["proposed_version"].
    """
    schema_name = proposal["target_schema"]
    table = proposal["target_table"]
    grain_keys = list(proposal["grain_keys"])
    key_positions = {key: i + 1 for i, key in enumerate(grain_keys)}

    table_rules: list[dict] = []
    column_rules: dict[str, list[dict]] = {}
    for rule in proposal["quality_rules"]:
        rendered = _describe_rule(rule, schema_name, table, grain_keys)
        if rule["kind"] in _TABLE_LEVEL_RULE_KINDS:
            table_rules.append(rendered)
        else:
            column_rules.setdefault(rule["column"], []).append(rendered)

    properties = []
    for column in proposal["columns"]:
        prop: dict = {
            "name": column["name"],
            "logicalType": column["logical_type"],
            "physicalType": column["physical_type"],
            "required": column["required"],
        }
        if column["name"] in key_positions:
            prop["primaryKey"] = True
            prop["primaryKeyPosition"] = key_positions[column["name"]]
        prop["description"] = column["description"]
        if column["name"] in column_rules:
            prop["quality"] = column_rules[column["name"]]
        properties.append(prop)

    grain_clause = "(" + ", ".join(grain_keys) + ")"
    table_object: dict = {
        "name": table,
        "physicalName": table,
        "logicalType": "object",
        "physicalType": "table",
        "description": (
            f"One row per distinct {grain_clause}. The {len(grain_keys)} "
            "grain columns are flagged primaryKey so sync generates the "
            "composite uniqueness test; that generated test is "
            "warn-severity by tool design at datacontract-cli 1.0.12, and "
            "the error-severity grain rule below is the enforcing twin "
            "(rule 5: uniqueness as a test, never a trusted constraint)."
        ),
        "dataGranularityDescription": f"One row per distinct {grain_clause}.",
        "properties": properties,
    }
    if table_rules:
        table_object["quality"] = table_rules

    custom = _custom_properties(provenance, proposal.get("decisions", []))
    custom.append({"property": "grain", "value": ", ".join(grain_keys)})

    words = table.split("_")
    return {
        "apiVersion": API_VERSION,
        "kind": "DataContract",
        "id": table,
        "name": " ".join([words[0].capitalize()] + words[1:]),
        "version": version,
        "status": "draft",
        "domain": DOMAIN,
        "dataProduct": DATA_PRODUCT,
        "tenant": TENANT,
        "description": {
            "purpose": proposal["purpose"],
            "usage": proposal["usage"],
            "limitations": proposal["limitations"],
        },
        "schema": [table_object],
        "servers": [
            {
                "server": "local",
                "type": "duckdb",
                "database": WAREHOUSE_DB,
                "schema": schema_name,
            }
        ],
        "customProperties": custom,
    }


class _LiteralDumper(yaml.SafeDumper):
    """SafeDumper that writes multi-line strings as literal blocks (`|`).

    The committed contracts write SQL rule queries as literal blocks; the
    default dumper renders the same string as an escaped double-quoted
    scalar, which lint accepts but a reviewer cannot read (Session N
    item 13). Single-line strings keep the default representation. The
    representer is registered on this subclass only, never on
    yaml.SafeDumper globally.
    """


def _represent_str(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_LiteralDumper.add_representer(str, _represent_str)


def dump_yaml(doc: dict, width: int = 88) -> str:
    """The one YAML serialization: block style, insertion order, literal
    blocks for multi-line strings. Shared by to_yaml and the terminal
    diff's normalization so both sides of a diff take the same path; the
    diff passes a width no scalar reaches, so one element is one line."""
    return yaml.dump(
        doc,
        Dumper=_LiteralDumper,
        sort_keys=False,
        width=width,
        allow_unicode=True,
        default_flow_style=False,
    )


def to_yaml(doc: dict, header_lines: list[str]) -> str:
    """Block-style YAML behind a comment header; same inputs, same bytes."""
    header = "".join(f"# {line}\n" for line in header_lines)
    return header + dump_yaml(doc)


# ---------------------------------------------------------------------------
# The amend stance: patch semantics over the committed document (D-35)

_PROVENANCE_KEYS = frozenset(
    {
        "proposedBy",
        "proposerVersion",
        "promptVersion",
        "modelId",
        "profileHash",
        "proposedAt",
        "proposerStance",
        "amendsContract",
    }
)


def canonical_contract_bytes(text_bytes: bytes) -> str:
    """sha256 over a committed contract's canonical bytes (Amendment I).

    Canonical bytes ARE the committed file's raw bytes exactly as read
    (S-Q-prep-5), because the committed file is itself the canonical
    artifact: git holds it, review approved it, and no re-serialization
    can make it more canonical than it already is. This is the same
    digest the harness staleness re-check computes over a non-profile
    governed input (raw bytes), so one definition serves both the
    `amendsContract` stamp and the staleness gate; a test pins the
    alignment (D-22 Amendment I).
    """
    return "sha256:" + hashlib.sha256(text_bytes).hexdigest()


def amends_contract_stamp(committed: dict, committed_bytes: bytes) -> str:
    """`<id>@<version>#sha256:<hash>` per D-22 Amendment I."""
    digest = canonical_contract_bytes(committed_bytes)
    return f"{committed['id']}@{committed['version']}#{digest}"


def _grain_texts(table_object: dict, grain_keys: list[str]) -> None:
    """Re-template the two grain prose fields after a grain_change.

    Uses the describe renderer's stable sentences: the committed
    hand-written prose is richer, but a stance never authors prose for a
    changed grain; the reviewer rewrites it in the editor if the
    template reads thin (D-24: the draft is the reviewer's to change).
    """
    clause = "(" + ", ".join(grain_keys) + ")"
    table_object["description"] = (
        f"One row per distinct {clause}. The {len(grain_keys)} "
        "grain columns are flagged primaryKey so sync generates the "
        "composite uniqueness test; that generated test is "
        "warn-severity by tool design at datacontract-cli 1.0.12, and "
        "the error-severity grain rule below is the enforcing twin "
        "(rule 5: uniqueness as a test, never a trusted constraint)."
    )
    table_object["dataGranularityDescription"] = (
        f"One row per distinct {clause}."
    )


def _find_rule(table_object: dict, signature: str) -> tuple[list, int] | None:
    """Locate a committed rule by its closed-list signature."""
    table_rules = table_object.get("quality", [])
    for index, entry in enumerate(table_rules):
        if rule_signature_of_committed(entry, "") == signature:
            return table_rules, index
    for prop in table_object.get("properties", []):
        rules = prop.get("quality", [])
        for index, entry in enumerate(rules):
            if rule_signature_of_committed(entry, prop["name"]) == signature:
                return rules, index
    return None


def _server_schema(document: dict) -> str:
    servers = document.get("servers", [])
    return servers[0].get("schema", "silver") if servers else "silver"


def _grain_keys_after(committed: dict, proposal: dict) -> list[str]:
    """The post-change grain: the declared grain_change's keys, else the
    committed primaryKey tuple in position order."""
    for change in proposal["changes"]:
        if change["kind"] == "grain_change":
            return [
                part.strip()
                for part in change["after"].split(",")
                if part.strip()
            ]
    keyed = [
        prop
        for prop in committed["schema"][0].get("properties", [])
        if prop.get("primaryKey")
    ]
    keyed.sort(key=lambda prop: prop.get("primaryKeyPosition", 0))
    return [prop["name"] for prop in keyed]


def apply_changes(committed: dict, proposal: dict) -> dict:
    """The declared changes applied as a patch over the committed
    document (D-35): nothing undeclared moves, so the diff is the
    declared change set by construction. The validator has already held
    every change true against the committed document; this function
    only applies, over a deepcopy (the committed dict is never mutated).
    A same-column required_change on an added column is the declared
    F-28 follow-up and is deliberately NOT applied here: additions enter
    optional and tighten in their own later amendment.
    """
    document = copy.deepcopy(committed)
    table_object = document["schema"][0]
    properties = table_object.setdefault("properties", [])
    by_name = {prop["name"]: prop for prop in properties}
    proposal_cols = {c["name"]: c for c in proposal["columns"]}
    rules_by_signature = {
        f"{r['kind']}:{r['column']}" if r["column"] else r["kind"]: r
        for r in proposal["quality_rules"]
    }
    added = {
        c["column"] for c in proposal["changes"] if c["kind"] == "add_column"
    }

    grain_keys = _grain_keys_after(committed, proposal)

    for change in proposal["changes"]:
        kind = change["kind"]
        column = change["column"]
        if kind == "no_change":
            continue
        if kind == "add_column":
            entry = proposal_cols[column]
            prop: dict = {
                "name": entry["name"],
                "logicalType": entry["logical_type"],
                "physicalType": entry["physical_type"],
                "required": False,
            }
            prop["description"] = entry["description"]
            properties.append(prop)
            by_name[column] = prop
        elif kind == "drop_column":
            properties.remove(by_name.pop(column))
        elif kind == "retype_column":
            prop = by_name[column]
            prop["physicalType"] = change["after"]
            entry = proposal_cols[column]
            prop["logicalType"] = entry["logical_type"]
        elif kind == "required_change":
            if column in added:
                continue  # the declared F-28 follow-up, deferred
            by_name[column]["required"] = change["after"] == "true"
        elif kind == "description_change":
            by_name[column]["description"] = change["after"]
        elif kind == "grain_change":
            for prop in properties:
                prop.pop("primaryKey", None)
                prop.pop("primaryKeyPosition", None)
            for position, key in enumerate(grain_keys, 1):
                by_name[key]["primaryKey"] = True
                by_name[key]["primaryKeyPosition"] = position
            _grain_texts(table_object, grain_keys)
            located = _find_rule(table_object, "grain_unique")
            if located is not None:
                rules, index = located
                rules[index] = _describe_rule(
                    {"kind": "grain_unique", "column": "", "values": []},
                    _server_schema(document),
                    table_object["name"],
                    grain_keys,
                )
        elif kind == "rule_change":
            if change["before"]:
                located = _find_rule(table_object, change["before"])
                if located is not None:
                    rules, index = located
                    del rules[index]
                    for prop in properties:
                        if prop.get("quality") == []:
                            del prop["quality"]
            if change["after"]:
                sig_kind, _, sig_column = change["after"].partition(":")
                rendered = _describe_rule(
                    rules_by_signature[change["after"]],
                    _server_schema(document),
                    table_object["name"],
                    grain_keys,
                )
                if sig_column:
                    by_name[sig_column].setdefault("quality", []).append(
                        rendered
                    )
                else:
                    table_object.setdefault("quality", []).append(rendered)
    return document


def _copy_entries(entries: list[dict]) -> list[dict]:
    return [copy.deepcopy(entry) for entry in entries]


def render_amend(
    committed: dict, proposal: dict, provenance: Provenance, version: str
) -> dict:
    """The amend render: patch, bump, restamp; everything else stands.

    The version parameter from the harness is deliberately ignored: the
    bump class derives from the declared change directions
    (validate.derive_bump; D-08, F-20; the human still sets the final
    version at approval), so a neutral amendment lands a patch bump and
    a narrowing one lands major; the harness's new-id fallback never
    fires because the patched id equals the committed id. Provenance is
    rebuilt per Appendix B plus the extras hook (proposerStance,
    amendsContract; D-22 Amendment I); every committed customProperty
    outside the provenance key set (the decision* record, the grain
    note) is carried deep-copied in its committed order, and the
    proposal's NEW decision keys append after it (a key already present
    is never re-valued; the validator refused it). status returns to
    draft: the human door re-approves every amendment (D-24).
    """
    del version  # derived from the declared changes, never passed in
    document = apply_changes(committed, proposal)
    document["version"] = next_version(
        committed["version"], derive_bump(proposal["changes"])
    )
    document["status"] = "draft"

    carried = [
        entry
        for entry in committed.get("customProperties", [])
        if entry.get("property") not in _PROVENANCE_KEYS
    ]
    carried_keys = {entry.get("property") for entry in carried}
    new_decisions = [
        decision
        for decision in proposal.get("decisions", [])
        if decision["key"] not in carried_keys
    ]
    custom = _custom_properties(provenance, [])
    custom.extend(_copy_entries(carried))
    for decision in new_decisions:
        custom.append({"property": decision["key"], "value": decision["value"]})
    grain_changed = any(
        c["kind"] == "grain_change" for c in proposal["changes"]
    )
    if grain_changed:
        keys_csv = ", ".join(_grain_keys_after(committed, proposal))
        for entry in custom:
            if entry.get("property") == "grain":
                entry["value"] = keys_csv
    document["customProperties"] = custom
    return document
