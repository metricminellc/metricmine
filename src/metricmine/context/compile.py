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
"""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from metricmine.engine.emitters import Emission
from metricmine.engine.reader import load_inputs, validate_mapping
from metricmine.profiling.canonical import canonical_bytes
from metricmine.profiling.writer import latest_version, write_if_changed

REPO_ROOT = Path(__file__).resolve().parents[3]

COMPILED_SCHEMA_VERSION = "1.1.0"


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


def build_compiled_context(repo_root: Path) -> dict:
    """The artifact content dict, pure: contracts in, no writes (D-30).

    Schema keys and manifests come from the same Emission the emitters
    use, so every registry key equals its emitted manifest_key literal by
    construction; that identity is what makes C3 pass. Every entry cites
    the MAPPING contract (its approval created the keys); the star
    contract governs the container and sits in sources.
    """
    inputs = load_inputs(repo_root)
    validate_mapping(inputs.mapping, inputs.silver, inputs.json_schema)
    emission = Emission(inputs.mapping, inputs.star)

    mapping = inputs.mapping
    properties = {p["name"]: p for p in emission.category["properties"]}
    typed_surface = _typed_surface(repo_root, emission.category_name)

    def entry(schema_key: str, entity_group: str, compiled: dict) -> dict:
        return {
            "schema_key": schema_key,
            "entity_group": entity_group,
            "contract_name": mapping["id"],
            "contract_version": mapping["version"],
            "compiled_context": compiled,
        }

    group = emission.category["entityGroup"]
    entries = [
        entry(
            emission.source_col_key,
            "source",
            {
                "manifest": emission.source_manifest,
                "role": "source",
                "source_table": emission.source_table,
            },
        ),
        # No values harvest for run: the run dim carries build-time
        # lineage; the registry describes meaning.
        entry(
            emission.run_col_key,
            "run",
            {
                "manifest": emission.run_manifest,
                "role": "run",
            },
        ),
        entry(
            emission.timeframe_col_key,
            "timeframe",
            {
                "fields": {
                    emission.time_column: _harvest(
                        properties[emission.time_column]
                    )
                },
                "manifest": emission.timeframe_manifest,
                "role": "timeframe",
                "time_grain": emission.time_grain,
            },
        ),
        entry(
            emission.dim_col_key,
            group,
            {
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
                "typed_surface": typed_surface,
            },
        ),
        entry(
            emission.fact_col_key,
            group,
            {
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

    return {
        "entries": entries,
        "schema_version": COMPILED_SCHEMA_VERSION,
        "sources": {
            "gold_contract": {
                "id": inputs.star["id"],
                "version": inputs.star["version"],
            },
            "mapping_contract": {
                "id": mapping["id"],
                "profileHash": _custom_properties(mapping)["profileHash"],
                "version": mapping["version"],
            },
            "silver_contract": {
                "id": inputs.silver["id"],
                "version": inputs.silver["version"],
            },
        },
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
