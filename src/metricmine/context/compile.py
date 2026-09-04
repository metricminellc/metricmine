"""Context compiler: governing contracts in, compiled-context artifact out.

Spec §4 (D-30): deterministic code, not an agent. It merges the governing
contracts' harvested context fields into one canonical artifact under
context/compiled/ (vNNNN.json plus meta sidecar, the profiles/ artifact
discipline, reused verbatim); the engine carries the newest artifact into
the emitted context_registry model as SQL VALUES literals. It writes
nowhere else and never reads the warehouse. ``build_compiled_context`` is
pure; ``main`` is config-driven from the context: block of
config/default.yaml, no CLI arguments, and fails closed with nothing
written on any error.

Since the multi-source fan-in (Arc 6, D-41; D-30 as amended) the artifact
carries every category: one dimensions entry and one measures entry per
mapping contract, each citing that mapping, plus ONE entry per shared
group (source, run, timeframe), each citing the star contract because
no single mapping owns a shared schema key. The registry's primary key
is the schema key, so shared keys appear exactly once. ``sources`` lists
the star contract and every mapping and silver contract in category
order (compiled schema 2.0.0).
"""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from metricmine.engine.emitters import Emission, StarEmission
from metricmine.engine.reader import (
    compiled_sources,
    load_inputs,
    validate_inputs,
)
from metricmine.profiling.canonical import canonical_bytes
from metricmine.profiling.writer import latest_version, write_if_changed

REPO_ROOT = Path(__file__).resolve().parents[3]

COMPILED_SCHEMA_VERSION = "2.0.0"


def _harvest(prop: dict) -> dict:
    """One field's compiled context: contract content only, verbatim."""
    return {
        "description": prop["description"],
        "logicalType": prop["logicalType"],
        "mappingRole": prop["mappingRole"],
        "physicalType": prop["physicalType"],
    }


def _custom_properties(contract: dict) -> dict:
    return {
        entry["property"]: entry["value"]
        for entry in contract.get("customProperties", [])
    }


def _typed_surface(repo_root: Path, category: str) -> str:
    """The category's typed surface per engine.marts (D-36; D-31/D-32 as
    amended): the materialized mart under ``table`` or ``both``, the
    projection view under ``view``. A missing key reads as ``both``. The
    pointer is config-derived deterministic content, so the registry and
    the engine's emission agree by construction.
    """
    config_path = Path(repo_root) / "config" / "default.yaml"
    engine_cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))[
        "engine"
    ]
    marts = engine_cfg.get("marts", "both")
    if marts in ("table", "both"):
        return f"mart_{category}_typed"
    return f"vw_{category}_typed"


def _conformed_keys(silver: dict, mapped: set[str]) -> dict[str, str]:
    """The silver contract's conformed keys (its `conformedKeys` custom
    property, `column=key` entries) restricted to the mapped columns:
    which typed columns join across categories, and under which key
    (the K1 gate, tests/test_conformed_keys.py, holds the declarations
    to the star's rules)."""
    raw = _custom_properties(silver).get("conformedKeys", "")
    keys: dict[str, str] = {}
    for entry in str(raw).split(","):
        column, _, key = entry.strip().partition("=")
        if column.strip() and key.strip() and column.strip() in mapped:
            keys[column.strip()] = key.strip()
    return keys


def _category_entries(
    repo_root: Path, emission: Emission, silver: dict
) -> list[dict]:
    """The two entries a mapping contract owns: its dimensions manifest
    and its measures manifest, both citing the mapping."""
    mapping = emission.mapping
    properties = {p["name"]: p for p in emission.category["properties"]}
    typed_surface = _typed_surface(repo_root, emission.category_name)
    group = emission.category["entityGroup"]
    conformed = _conformed_keys(silver, set(properties))

    def entry(schema_key: str, compiled: dict) -> dict:
        return {
            "schema_key": schema_key,
            "entity_group": group,
            "contract_name": mapping["id"],
            "contract_version": mapping["version"],
            "compiled_context": compiled,
        }

    return [
        entry(
            emission.dim_col_key,
            {
                "category": emission.category_name,
                "conformed_keys": conformed,
                "derived_identifiers": {
                    identifier["name"]: {
                        "derivation": identifier["derivation"],
                        "of": identifier["of"],
                        "source": identifier["source"],
                    }
                    for identifier in emission.derived_identifiers
                },
                "fields": {
                    name: _harvest(properties[name])
                    for name in emission.dim_payload_columns
                },
                "manifest": emission.dim_manifest,
                "role": "dimensions",
                "source_table": emission.source_table,
                "time_column": emission.time_column,
                "time_grain": emission.time_grain,
                "typed_surface": typed_surface,
            },
        ),
        entry(
            emission.fact_col_key,
            {
                "category": emission.category_name,
                "fields": {
                    name: _harvest(properties[name])
                    for name in emission.measure_manifest
                },
                "manifest": emission.measure_manifest,
                "role": "measures",
                "source_table": emission.source_table,
                "typed_surface": typed_surface,
            },
        ),
    ]


def _shared_entries(star: StarEmission) -> list[dict]:
    """The three shared-group entries, once per star, citing the star
    contract: the source group names every mapped table, the run group
    carries build lineage only, the timeframe group is the conformed
    calendar with every category's declared time column and grain."""
    contract = star.star

    def entry(schema_key: str, entity_group: str, compiled: dict) -> dict:
        return {
            "schema_key": schema_key,
            "entity_group": entity_group,
            "contract_name": contract["id"],
            "contract_version": contract["version"],
            "compiled_context": compiled,
        }

    return [
        entry(
            star.source_col_key,
            "source",
            {
                "manifest": star.source_manifest,
                "role": "source",
                "source_tables": [
                    emission.source_table for emission in star.categories
                ],
            },
        ),
        # No values harvest for run: the run dim carries build-time
        # lineage; the registry describes meaning.
        entry(
            star.run_col_key,
            "run",
            {
                "manifest": star.run_manifest,
                "role": "run",
            },
        ),
        entry(
            star.timeframe_col_key,
            "timeframe",
            {
                "categories": {
                    emission.category_name: {
                        "time_column": emission.time_column,
                        "time_grain": emission.time_grain,
                        "field": _harvest(
                            next(
                                p
                                for p in emission.category["properties"]
                                if p["name"] == emission.time_column
                            )
                        ),
                    }
                    for emission in star.categories
                },
                "fields": {
                    "grain": {
                        "description": (
                            "The declared time grain of the category the"
                            " period belongs to (minute, hour, day, week,"
                            " month, quarter, year)."
                        ),
                        "logicalType": "string",
                        "physicalType": "VARCHAR",
                    },
                    "period_start": {
                        "description": (
                            "The category's declared time column truncated"
                            " to its grain and rendered canonically; equal"
                            " periods at equal grain hash to one row"
                            " whichever category minted them (the conformed"
                            " calendar, D-17 Amendment R)."
                        ),
                        "logicalType": "date",
                        "physicalType": "TIMESTAMP",
                    },
                },
                "manifest": star.timeframe_manifest,
                "role": "timeframe",
            },
        ),
    ]


def build_compiled_context(repo_root: Path) -> dict:
    """The artifact content dict, pure: contracts in, no writes (D-30).

    Schema keys and manifests come from the same Emission the emitters
    use, so every registry key equals its emitted manifest_key literal by
    construction; that identity is what makes C3 pass. Category entries
    cite their MAPPING contract (its approval created the keys); shared
    entries cite the star contract, which governs the container; every
    contract sits in sources.
    """
    inputs = load_inputs(repo_root)
    validate_inputs(inputs)
    star = StarEmission(inputs.mappings, inputs.star)

    entries = _shared_entries(star)
    for emission in star.categories:
        silver = inputs.silvers[emission.source_model]
        entries.extend(_category_entries(repo_root, emission, silver))

    sources = compiled_sources(inputs)
    by_id = {mapping["id"]: mapping for mapping in inputs.mappings}
    for cited in sources["mapping_contracts"]:
        cited["profileHash"] = _custom_properties(by_id[cited["id"]])[
            "profileHash"
        ]

    return {
        "entries": entries,
        "schema_version": COMPILED_SCHEMA_VERSION,
        "sources": sources,
    }


def main() -> int:
    try:
        config_path = REPO_ROOT / "config" / "default.yaml"
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))["context"]
        compiled_dir = REPO_ROOT / cfg["output_dir"]
        artifact = build_compiled_context(REPO_ROOT)
        # The sidecar is determinism-exempt run metadata; the artifact
        # bytes themselves carry deterministic content only.
        meta = {
            "compiled_schema_version": COMPILED_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "python_version": platform.python_version(),
        }
        written = write_if_changed(
            compiled_dir, canonical_bytes(artifact), meta
        )
    except Exception as exc:  # fail-closed: nothing written on any failure
        print(f"ERROR: {exc}")
        return 1
    if written is None:
        current = latest_version(compiled_dir)
        print(f"compiled context unchanged (v{current:04d} already current)")
    else:
        print(f"wrote {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
