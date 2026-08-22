"""Pre-N probe P2 (August 21, 2026): proposal schemas that survive structured-outputs constraints.

Runs offline (no API key). Proves:
  1. the frozen mapping-contract.schema.json is NOT structured-outputs
     compatible (transform_schema raises);
  2. a purpose-built mapping PROPOSAL schema passes transform_schema and
     stays inside the documented limits (24 optional params, 16 unions);
  3. a hand-built proposal (mirroring contracts/gold_invoice_lines_mapping
     v1.1.0) renders to an ODCS document that validates against the FROZEN
     schema with jsonschema, so the frozen schema stays the validator;
  4. the same for a silver cleanup PROPOSAL schema (render shape only; the
     silver plane has no frozen JSON schema, datacontract lint gates it).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
from anthropic import transform_schema

# Reruns from docs/verification/evidence/<this file> (parents[3] is the repo
# root) or from any checkout via METRICMINE_REPO.
import os
REPO = Path(os.environ.get("METRICMINE_REPO") or Path(__file__).resolve().parents[3])
FROZEN = json.loads((REPO / "docs/spec/engine/mapping-contract.schema.json").read_text())

# ---------------------------------------------------------------- helpers
def count_optionals_and_unions(schema: dict) -> tuple[int, int]:
    """Count optional properties and union-typed params the way the API
    limits describe them (optional = declared but not required; union =
    anyOf or a type array)."""
    optionals = unions = 0

    def walk(node):
        nonlocal optionals, unions
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                req = set(node.get("required", []))
                for name, sub in node["properties"].items():
                    if name not in req:
                        optionals += 1
            if isinstance(node.get("type"), list) or "anyOf" in node:
                unions += 1
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)
    return optionals, unions


# ------------------------------------------------- 1. frozen schema fails
try:
    transform_schema(FROZEN)
    print("1. frozen schema: transform_schema PASSED (unexpected)")
except Exception as exc:  # noqa: BLE001
    print(f"1. frozen schema: transform_schema RAISED {type(exc).__name__}: {exc}")

# --------------------------------------- 2. mapping PROPOSAL schema (draft)
FIELD = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "logical_type", "physical_type", "required", "mapping_role", "description"],
    "properties": {
        "name": {"type": "string", "description": "Exact silver column name from the profile."},
        "logical_type": {"type": "string", "enum": ["string", "integer", "number", "boolean", "date"]},
        "physical_type": {"type": "string", "description": "DuckDB physical type as profiled, e.g. VARCHAR, INTEGER, DECIMAL(10,2), TIMESTAMP."},
        "required": {"type": "boolean", "description": "true when the profile shows null_rate == 0 and the column is identity-bearing."},
        "mapping_role": {"type": "string", "enum": ["dimension", "measure", "time"]},
        "description": {"type": "string", "description": "One sentence of business meaning citing profile evidence."},
    },
}
DEGENERATE_ID = {
    "type": "object",
    "additionalProperties": False,
    "required": ["source", "name", "of"],
    "properties": {
        "source": {"type": "string", "enum": ["column", "derived"]},
        "name": {"type": "string"},
        "of": {
            "type": "array",
            "items": {"type": "string"},
            "description": "For source=derived: the silver columns hashed by canonical-key-v2, in order. For source=column: empty.",
        },
    },
}
AGGREGATION = {
    "type": "object",
    "additionalProperties": False,
    "required": ["field", "function"],
    "properties": {
        "field": {"type": "string"},
        "function": {"type": "string", "enum": ["sum", "min", "max", "avg", "count"]},
    },
}
MAPPING_PROPOSAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "category_name", "entity_group", "source_table", "time_column", "time_grain",
        "grain_type", "degenerate_identifiers", "aggregations", "grain_rationale",
        "fields", "category_description", "purpose", "usage", "limitations",
    ],
    "properties": {
        "category_name": {"type": "string", "description": "lowercase snake_case; never starts with dim_, fact_, vw_, silver_, bronze_, stg_; never context_registry."},
        "entity_group": {"type": "string"},
        "source_table": {"type": "string", "description": "silver.<table> exactly as the profile names it."},
        "time_column": {"type": "string"},
        "time_grain": {"type": "string", "enum": ["minute", "hour", "day", "week", "month", "quarter", "year"]},
        "grain_type": {"type": "string", "enum": ["transaction", "aggregated"]},
        "degenerate_identifiers": {"type": "array", "items": DEGENERATE_ID, "description": "Required non-empty when grain_type=transaction; empty when aggregated."},
        "aggregations": {"type": "array", "items": AGGREGATION, "description": "Required non-empty when grain_type=aggregated; empty when transaction."},
        "grain_rationale": {"type": "string", "description": "Why this grain, citing row_count and duplicate_row_rate from the profile."},
        "fields": {"type": "array", "items": FIELD, "minItems": 1},
        "category_description": {"type": "string"},
        "purpose": {"type": "string"},
        "usage": {"type": "string"},
        "limitations": {"type": "string"},
    },
}
t = transform_schema(MAPPING_PROPOSAL_SCHEMA)
opt, uni = count_optionals_and_unions(MAPPING_PROPOSAL_SCHEMA)
print(f"2. mapping proposal schema: transform_schema OK; optional params={opt} (limit 24); unions={uni} (limit 16)")
print("   transform changed the schema:", json.dumps(t, sort_keys=True) != json.dumps(MAPPING_PROPOSAL_SCHEMA, sort_keys=True))

# ---------------------------- 3. render a proposal -> ODCS, validate FROZEN
proposal = {
    "category_name": "invoice_lines",
    "entity_group": "invoice_lines",
    "source_table": "silver.silver_invoice_lines",
    "time_column": "invoiced_at",
    "time_grain": "minute",
    "grain_type": "transaction",
    "degenerate_identifiers": [
        {"source": "derived", "name": "line_identity", "of": ["invoice_id", "stock_code", "quantity", "unit_price"]}
    ],
    "aggregations": [],
    "grain_rationale": "duplicate_row_rate 0.0 at 44721 rows; the silver grain tuple is unique.",
    "fields": [
        {"name": "invoice_id", "logical_type": "string", "physical_type": "VARCHAR", "required": True, "mapping_role": "dimension", "description": "Invoice number; C prefix marks a cancellation."},
        {"name": "is_cancellation", "logical_type": "boolean", "physical_type": "BOOLEAN", "required": True, "mapping_role": "dimension", "description": "Cancellation flag."},
        {"name": "stock_code", "logical_type": "string", "physical_type": "VARCHAR", "required": True, "mapping_role": "dimension", "description": "Product code as landed."},
        {"name": "product_description", "logical_type": "string", "physical_type": "VARCHAR", "required": False, "mapping_role": "dimension", "description": "Product description; nulls retained."},
        {"name": "quantity", "logical_type": "integer", "physical_type": "INTEGER", "required": True, "mapping_role": "measure", "description": "Units on the line."},
        {"name": "invoiced_at", "logical_type": "date", "physical_type": "TIMESTAMP", "required": True, "mapping_role": "time", "description": "Invoice timestamp."},
        {"name": "unit_price", "logical_type": "number", "physical_type": "DECIMAL(10,2)", "required": True, "mapping_role": "measure", "description": "Unit price in sterling."},
        {"name": "customer_id", "logical_type": "integer", "physical_type": "INTEGER", "required": False, "mapping_role": "dimension", "description": "Customer identifier; null on guest checkouts."},
        {"name": "country", "logical_type": "string", "physical_type": "VARCHAR", "required": True, "mapping_role": "dimension", "description": "Customer country as landed."},
    ],
    "category_description": "One fact category: line-level retail sales.",
    "purpose": "Declares how silver.silver_invoice_lines maps into the unified event star.",
    "usage": "Engine input only.",
    "limitations": "Cancellation lines flow through retained-and-flagged.",
}


def render_mapping(p: dict, *, profile_hash: str, proposed_at: str, model_id: str,
                   prompt_version: str, proposer_version: str, version: str) -> dict:
    """Deterministic proposal JSON -> ODCS mapping contract document (dict).
    Key order here IS the canonical order; the YAML writer keeps it."""
    if p["grain_type"] == "transaction":
        grain = {
            "type": "transaction",
            "degenerateIdentifiers": [
                ({"source": "column", "name": d["name"]} if d["source"] == "column"
                 else {"source": "derived", "name": d["name"], "derivation": "canonical-key-v2", "of": list(d["of"])})
                for d in p["degenerate_identifiers"]
            ],
        }
    else:
        grain = {"type": "aggregated", "aggregations": {a["field"]: a["function"] for a in p["aggregations"]}}
    return {
        "apiVersion": "v3.1.0",
        "kind": "DataContract",
        "id": f"gold_{p['category_name']}_mapping",
        "name": f"Gold mapping, {p['category_name']} category",
        "version": version,
        "status": "draft",
        "domain": "retail",
        "dataProduct": "metricmine",
        "tenant": "metricmine",
        "description": {"purpose": p["purpose"], "usage": p["usage"], "limitations": p["limitations"]},
        "schema": [{
            "name": p["category_name"],
            "logicalType": "object",
            "physicalType": "mapping",
            "description": p["category_description"],
            "entityGroup": p["entity_group"],
            "sourceTable": p["source_table"],
            "timeColumn": p["time_column"],
            "timeGrain": p["time_grain"],
            "grain": grain,
            "properties": [
                {"name": f["name"], "logicalType": f["logical_type"], "physicalType": f["physical_type"],
                 "required": f["required"], "mappingRole": f["mapping_role"], "description": f["description"]}
                for f in p["fields"]
            ],
        }],
        "servers": [{"server": "local", "type": "duckdb", "database": "warehouse/metricmine.duckdb", "schema": "gold"}],
        "customProperties": [
            {"property": "proposedBy", "value": "gold-mapping-proposer"},
            {"property": "proposerVersion", "value": proposer_version},
            {"property": "promptVersion", "value": prompt_version},
            {"property": "modelId", "value": model_id},
            {"property": "profileHash", "value": profile_hash},
            {"property": "proposedAt", "value": proposed_at},
            {"property": "decisionGrainRationale", "value": p["grain_rationale"]},
        ],
    }


doc = render_mapping(
    proposal,
    profile_hash="sha256:e65bee8117b65958b8c4741b43509ece19a581dd1d6bad9a7e1da9b67b0b5fcd",
    proposed_at="2026-08-21",
    model_id="claude-sonnet-5",
    prompt_version="0.1.0",
    proposer_version="0.1.0",
    version="1.2.0",
)
jsonschema.validate(instance=doc, schema=FROZEN)
print("3. rendered mapping proposal validates against the FROZEN schema: OK")

# Groundedness check against the committed silver profile
profile = json.loads((REPO / "profiles/silver.silver_invoice_lines/v0001.json").read_text())
profile_cols = {c["name"] for c in profile["dataset"]["columns"]}
referenced = {f["name"] for f in proposal["fields"]} | {proposal["time_column"]}
for d in proposal["degenerate_identifiers"]:
    referenced |= set(d["of"])
missing = referenced - profile_cols
print(f"   groundedness vs silver v0001: referenced={len(referenced)} missing={sorted(missing)}")
print(f"   profile content_hash field present: {profile['content_hash'][:16]}...; schema_version={profile['schema_version']}")

# A negative case: a hallucinated column must be caught by the validator (not the schema)
bad = json.loads(json.dumps(proposal))
bad["fields"].append({"name": "region", "logical_type": "string", "physical_type": "VARCHAR", "required": False, "mapping_role": "dimension", "description": "hallucinated"})
bad_ref = {f["name"] for f in bad["fields"]}
print(f"   negative case: hallucinated column caught by groundedness = {sorted(bad_ref - profile_cols)}")

# Unordered diff vs the committed contract: every first-class mapping element must agree
committed = __import__("yaml").safe_load((REPO / "contracts/gold_invoice_lines_mapping.odcs.yaml").read_text())
cs, ds = committed["schema"][0], doc["schema"][0]
same = all(cs[k] == ds[k] for k in ("name", "entityGroup", "sourceTable", "timeColumn", "timeGrain", "grain"))
same_fields = [(p["name"], p["logicalType"], p["physicalType"], p["required"], p["mappingRole"]) for p in cs["properties"]] == \
              [(p["name"], p["logicalType"], p["physicalType"], p["required"], p["mappingRole"]) for p in ds["properties"]]
print(f"   first-class elements equal to committed v1.1.0: header={same} fields={same_fields}")

# -------------------------------------- 4. silver cleanup PROPOSAL schema
COLUMN_ACTION = {
    "type": "object",
    "additionalProperties": False,
    "required": ["source_column", "action", "target_name", "logical_type", "physical_type", "required", "null_handling", "rationale"],
    "properties": {
        "source_column": {"type": "string", "description": "Exact bronze column name from the profile."},
        "action": {"type": "string", "enum": ["keep", "rename", "cast", "rename_and_cast", "drop", "derive_flag"]},
        "target_name": {"type": "string", "description": "Silver column name (snake_case). Equal to source_column for keep/cast; empty string for drop."},
        "logical_type": {"type": "string", "enum": ["string", "integer", "number", "boolean", "date"]},
        "physical_type": {"type": "string", "description": "Target DuckDB type, e.g. VARCHAR, INTEGER, DECIMAL(10,2), TIMESTAMP, BOOLEAN."},
        "required": {"type": "boolean"},
        "null_handling": {"type": "string", "enum": ["retain_null", "fail_on_null", "not_applicable"]},
        "rationale": {"type": "string", "description": "One sentence citing profile evidence (null_rate, distinct_count, samples)."},
    },
}
SILVER_PROPOSAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["target_table", "columns", "dedupe_strategy", "dedupe_keys", "grain_keys", "decisions", "purpose", "usage", "limitations"],
    "properties": {
        "target_table": {"type": "string", "description": "silver table name, snake_case, starting with silver_."},
        "columns": {"type": "array", "items": COLUMN_ACTION, "minItems": 1},
        "dedupe_strategy": {"type": "string", "enum": ["none", "exact_duplicates", "exact_duplicates_and_clock_drift"]},
        "dedupe_keys": {"type": "array", "items": {"type": "string"}},
        "grain_keys": {"type": "array", "items": {"type": "string"}, "minItems": 1, "description": "Target column names forming the declared grain; rendered as primaryKey positions and the error-severity grain rule."},
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["key", "value", "rationale"],
                "properties": {"key": {"type": "string"}, "value": {"type": "string"}, "rationale": {"type": "string"}},
            },
            "description": "Rendered as customProperties decision* keys, the convention silver v1.1.0 established.",
        },
        "purpose": {"type": "string"},
        "usage": {"type": "string"},
        "limitations": {"type": "string"},
    },
}
transform_schema(SILVER_PROPOSAL_SCHEMA)
opt, uni = count_optionals_and_unions(SILVER_PROPOSAL_SCHEMA)
print(f"4. silver cleanup proposal schema: transform_schema OK; optional params={opt} (limit 24); unions={uni} (limit 16)")

Path("/tmp/gold-mapping-proposal.schema.json").write_text(json.dumps(MAPPING_PROPOSAL_SCHEMA, indent=2) + "\n")
Path("/tmp/silver-cleanup-proposal.schema.json").write_text(json.dumps(SILVER_PROPOSAL_SCHEMA, indent=2) + "\n")
print("schema drafts written to /tmp/*-proposal.schema.json")
sys.exit(0)
