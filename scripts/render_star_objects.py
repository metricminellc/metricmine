"""Render a category's gold star contract objects from its mapping contract.

Governing decisions: D-17 (the unified event star), D-28 (contract-declared
severity), D-29 (the engine), D-41 (the multi-source proof). The gold star
contract is pattern-derived and human-approved (rule 16); every category
it declares carries the same three objects (the values and columns
dimensions and the fact) with the same conservation rules (C1, C2, C4,
C5, grain and key uniqueness). This script renders those blocks for ONE
category from its approved mapping contract, so adding a source to the
star is a paste into the contract and a review, never hand-transcription
of a 200-line pattern. It is a scaffold tool in the export-dbt-models
tradition (rule 11): its output is a proposal the human pastes into
contracts/gold_unified_event_star.odcs.yaml, reviews, and versions. It
writes nothing.

Usage:
    uv run python scripts/render_star_objects.py contracts/gold_<category>_mapping.odcs.yaml

Prints the three schema objects, then the C3 union line the registry's
coverage rule needs for the category.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

_BATCH_WHERE = (
    "{% if var('mm_batch_floor', none) is not none %} WHERE captured_at"
    " >= TIMESTAMP '{{ var(\"mm_batch_floor\") }}' {% endif %}"
)
_BATCH_AND = (
    "{% if var('mm_batch_floor', none) is not none %} AND captured_at"
    " >= TIMESTAMP '{{ var(\"mm_batch_floor\") }}' {% endif %}"
)
_BATCH_AND_F = (
    "{% if var('mm_batch_floor', none) is not none %} AND f.captured_at"
    " >= TIMESTAMP '{{ var(\"mm_batch_floor\") }}' {% endif %}"
)

_TEXT_LOGICAL = {"string"}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line else line for line in text.splitlines())


def _c5_compare(prop: dict, time_column: str, time_grain: str) -> str:
    name = prop["name"]
    if name == time_column:
        return f"v.{name} IS DISTINCT FROM date_trunc('{time_grain}', s.{name})"
    if prop["logicalType"] in _TEXT_LOGICAL:
        return f"v.{name} IS DISTINCT FROM lower(s.{name})"
    return f"v.{name} IS DISTINCT FROM s.{name}"


def render(mapping_path: Path) -> str:
    mapping = _load(mapping_path)
    category = mapping["schema"][0]
    name = category["name"]
    source_table = category["sourceTable"]
    time_column = category["timeColumn"]
    time_grain = category["timeGrain"]
    grain = category["grain"]
    properties = category["properties"]
    dims = [p["name"] for p in properties if p["mappingRole"] == "dimension"]
    measures = [p["name"] for p in properties if p["mappingRole"] == "measure"]
    derived = [
        d for d in grain.get("degenerateIdentifiers", []) if d["source"] == "derived"
    ]
    if grain["type"] != "transaction" or len(derived) != 1:
        raise SystemExit(
            "this renderer covers transaction grain with exactly one derived"
            " degenerate identifier (the committed pattern); other shapes"
            " are hand-authored"
        )
    identity = derived[0]
    identity_name = identity["name"]
    of_sorted = sorted(identity["of"], key=str.lower)
    identity_struct = ",\n".join(
        f"              {col} := cast({col} as varchar)" for col in of_sorted
    )
    # C5 compares field by field in the typed surface's column order
    # (the engine's projection: dimensions in declared order, the time
    # column, then measures in declared order), so the rule reads like
    # the surface it audits.
    by_role = {p["name"]: p for p in properties}
    surface_order = (
        [by_role[n] for n in dims]
        + [by_role[time_column]]
        + [by_role[n] for n in measures]
    )
    compares = "\n".join(
        f"             OR {_c5_compare(p, time_column, time_grain)}"
        if i
        else f"          WHERE {_c5_compare(p, time_column, time_grain)}"
        for i, p in enumerate(surface_order)
    )
    typed_view = f"vw_{name}_typed"
    dim_values = f"dim_{name}_values"
    dim_columns = f"dim_{name}_columns"
    fact = f"fact_{name}_values"
    measures_phrase = ", ".join(measures)
    dims_phrase = ", ".join(dims)

    return f"""  - name: {dim_values}
    physicalName: {dim_values}
    logicalType: object
    physicalType: table
    description: >
      {name} category group, values side: the dimension-attribute payload
      per the mapping contract (the dimension-role fields {dims_phrase}
      plus the derived {identity_name} degenerate identifier), deduplicated
      by content key, row-unique at transaction grain because
      {identity_name} carries the declared silver grain tuple as one
      canonical_key v2 digest. Generic column names (dim_*) keep the
      physical shape source-invariant; the category lives in the table
      name. Engine-emitted (D-09).
    properties:
      - name: dim_hash_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        primaryKey: true
        primaryKeyPosition: 1
        description: "Record key over the dimension payload (D-18)."
      - name: dim_col_hash_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        description: >
          Schema key of the dimension manifest; resolves in
          {dim_columns}. A new mapping dimension mints a NEW schema
          key here (D-17).
      - name: dim_values
        logicalType: string
        physicalType: VARCHAR
        required: true
        description: "Dimension payload: canonical JSON text (C4-gated)."
      - name: loaded_at
        logicalType: date
        physicalType: TIMESTAMP
        required: true
        description: Audit stamp; outside every hashed payload (rule 13).
      - name: captured_at
        logicalType: date
        physicalType: TIMESTAMP
        required: true
        description: >
          Capture watermark carried from silver (D-38): first-seen
          (minimum) capture timestamp over the silver rows behind this
          payload. Outside every hashed payload (rule 13). Required from
          the first version: the model populates it on every row from
          its first build (F-49).
    quality:
      - type: library
        metric: rowCount
        description: The dimension is never empty once the star builds.
        severity: error
        mustBeGreaterThan: 0
      - type: sql
        description: >
          Content-key uniqueness: the error-severity twin of the
          primaryKey flag.
        severity: error
        query: |
          SELECT COUNT(*) FROM (
            SELECT dim_hash_id FROM {{{{ ref('{dim_values}') }}}}
            {_BATCH_WHERE}
            GROUP BY dim_hash_id HAVING COUNT(*) > 1
          )
        mustBe: 0
      - type: sql
        description: "C4: every dimension payload parses as valid JSON."
        severity: error
        query: |
          SELECT COUNT(*) FROM {{{{ ref('{dim_values}') }}}}
          WHERE NOT json_valid(dim_values)
          {_BATCH_AND}
        mustBe: 0

  - name: {dim_columns}
    physicalName: {dim_columns}
    logicalType: object
    physicalType: table
    description: >
      {name} category group, columns side: one row per distinct category
      manifest: the dimension-payload field set and the measure-payload
      field set both live here, keyed by schema key. A new mapping
      dimension announces itself as a new row here plus a registry row
      (D-17).
    properties:
      - name: dim_col_hash_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        primaryKey: true
        primaryKeyPosition: 1
        description: >
          Schema key over a category manifest in declared order (D-18).
      - name: dim_columns
        logicalType: string
        physicalType: VARCHAR
        required: true
        description: "Category manifest: compact JSON array in declared order."
      - name: loaded_at
        logicalType: date
        physicalType: TIMESTAMP
        required: true
        description: Audit stamp; outside every hashed payload (rule 13).
    quality:
      - type: library
        metric: rowCount
        description: The dimension is never empty once the star builds.
        severity: error
        mustBeGreaterThan: 0
      - type: sql
        description: >
          Schema-key uniqueness: the error-severity twin of the primaryKey
          flag.
        severity: error
        query: |
          SELECT COUNT(*) FROM (
            SELECT dim_col_hash_id FROM {{{{ ref('{dim_columns}') }}}}
            GROUP BY dim_col_hash_id HAVING COUNT(*) > 1
          )
        mustBe: 0

  - name: {fact}
    physicalName: {fact}
    logicalType: object
    physicalType: table
    description: >
      The {name} fact: measure payload ({measures_phrase} per the mapping
      contract), manifest reference, and group-key references. One row
      per declared transaction grain: one row per {source_table} row (the
      C1 conservation arithmetic). Composite primary key (fact, source,
      timeframe, dim) hashes; run_hash_id is deliberately NON-key so a
      contract version bump never mints duplicate facts (D-17).
      Engine-emitted (D-09).
    dataGranularityDescription: >
      Transaction grain per the mapping contract: one row per
      {source_table} row, made row-unique by the derived {identity_name}
      carried in the dimension payload.
    properties:
      - name: fact_hash_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        primaryKey: true
        primaryKeyPosition: 1
        description: "Record key over the measure payload (D-18)."
      - name: source_hash_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        primaryKey: true
        primaryKeyPosition: 2
        description: "Group key: resolves in gold.dim_source_values (C2)."
      - name: timeframe_hash_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        primaryKey: true
        primaryKeyPosition: 3
        description: "Group key: resolves in gold.dim_timeframe_values (C2)."
      - name: dim_hash_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        primaryKey: true
        primaryKeyPosition: 4
        description: "Group key: resolves in gold.{dim_values} (C2)."
      - name: run_hash_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        description: >
          Non-key lineage reference: resolves in gold.dim_run_values (C2)
          but never participates in the fact grain (D-17).
      - name: fact_col_hash_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        description: >
          Schema key of the measure manifest: resolves in
          gold.{dim_columns} (C2).
      - name: fact_values
        logicalType: string
        physicalType: VARCHAR
        required: true
        description: "Measure payload: canonical JSON text (C4-gated)."
      - name: loaded_at
        logicalType: date
        physicalType: TIMESTAMP
        required: true
        description: Audit stamp; outside every hashed payload (rule 13).
      - name: captured_at
        logicalType: date
        physicalType: TIMESTAMP
        required: true
        description: >
          Capture watermark carried from silver (D-38): the contributing
          silver row's capture timestamp, per fact row. Outside every
          hashed payload (rule 13). Required from the first version: the
          model populates it on every row from its first build (F-49).
    quality:
      - type: library
        metric: rowCount
        description: The fact is never empty once the star builds.
        severity: error
        mustBeGreaterThan: 0
      - type: sql
        description: >
          C1 conservation: silver rows in scope equal fact rows at
          transaction grain. Schema-qualified silver reference by design:
          a missing referenced table catalog-errors loudly rather than
          skipping (F-08).
        severity: error
        query: |
          SELECT (SELECT COUNT(*) FROM {source_table})
               - (SELECT COUNT(*) FROM {{{{ ref('{fact}') }}}})
        mustBe: 0
      - type: sql
        description: >
          C5 field-level reconciliation: every silver row joins the typed
          surface on the derived {identity_name} and every mapped field
          matches its served value (text fields lowercased per D-18;
          {time_column} at the declared {time_grain} grain; null-safe
          compare). Zero rows may disagree.
        severity: error
        query: |
          SELECT COUNT(*) FROM (
            SELECT *, sha256(lower(to_json(struct_pack(
{identity_struct}
            )))) AS {identity_name}
            FROM {source_table}
            {_BATCH_WHERE}
          ) s
          LEFT JOIN {{{{ ref('{typed_view}') }}}} v USING ({identity_name})
{compares}
        mustBe: 0
      - type: sql
        description: "C2: every source_hash_id resolves in dim_source_values."
        severity: error
        query: |
          SELECT COUNT(*) FROM {{{{ ref('{fact}') }}}} f
          WHERE NOT EXISTS (
            SELECT 1 FROM {{{{ ref('dim_source_values') }}}} d
            WHERE d.source_hash_id = f.source_hash_id
          )
          {_BATCH_AND_F}
        mustBe: 0
      - type: sql
        description: "C2: every timeframe_hash_id resolves in dim_timeframe_values."
        severity: error
        query: |
          SELECT COUNT(*) FROM {{{{ ref('{fact}') }}}} f
          WHERE NOT EXISTS (
            SELECT 1 FROM {{{{ ref('dim_timeframe_values') }}}} d
            WHERE d.timeframe_hash_id = f.timeframe_hash_id
          )
          {_BATCH_AND_F}
        mustBe: 0
      - type: sql
        description: "C2: every dim_hash_id resolves in {dim_values}."
        severity: error
        query: |
          SELECT COUNT(*) FROM {{{{ ref('{fact}') }}}} f
          WHERE NOT EXISTS (
            SELECT 1 FROM {{{{ ref('{dim_values}') }}}} d
            WHERE d.dim_hash_id = f.dim_hash_id
          )
          {_BATCH_AND_F}
        mustBe: 0
      - type: sql
        description: >
          C2: every run_hash_id (non-key) resolves in dim_run_values.
        severity: error
        query: |
          SELECT COUNT(*) FROM {{{{ ref('{fact}') }}}} f
          WHERE NOT EXISTS (
            SELECT 1 FROM {{{{ ref('dim_run_values') }}}} d
            WHERE d.run_hash_id = f.run_hash_id
          )
          {_BATCH_AND_F}
        mustBe: 0
      - type: sql
        description: >
          C2: every fact_col_hash_id (measure manifest) resolves in
          {dim_columns}.
        severity: error
        query: |
          SELECT COUNT(*) FROM {{{{ ref('{fact}') }}}} f
          WHERE NOT EXISTS (
            SELECT 1 FROM {{{{ ref('{dim_columns}') }}}} d
            WHERE d.dim_col_hash_id = f.fact_col_hash_id
          )
          {_BATCH_AND_F}
        mustBe: 0
      - type: sql
        description: >
          Grain enforcement: zero duplicate (fact, source, timeframe, dim)
          key tuples, the error-severity twin of the composite primaryKey
          flag, whose generated test is warn-hardcoded (F-08).
        severity: error
        query: |
          SELECT COUNT(*) FROM (
            SELECT fact_hash_id, source_hash_id, timeframe_hash_id, dim_hash_id
            FROM {{{{ ref('{fact}') }}}}
            {_BATCH_WHERE}
            GROUP BY fact_hash_id, source_hash_id, timeframe_hash_id, dim_hash_id
            HAVING COUNT(*) > 1
          )
        mustBe: 0
      - type: sql
        description: "C4: every measure payload parses as valid JSON."
        severity: error
        query: |
          SELECT COUNT(*) FROM {{{{ ref('{fact}') }}}}
          WHERE NOT json_valid(fact_values)
          {_BATCH_AND}
        mustBe: 0

C3 union line for the registry's coverage rule (add under the existing
UNION branches):
            UNION
            SELECT dim_col_hash_id FROM {{{{ ref('{dim_columns}') }}}}
"""


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    mapping_path = Path(argv[1])
    if not mapping_path.is_absolute():
        mapping_path = REPO_ROOT / mapping_path
    sys.stdout.write(render(mapping_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
