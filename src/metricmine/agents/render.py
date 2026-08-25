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

from dataclasses import dataclass, field
from typing import Mapping

import yaml

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
