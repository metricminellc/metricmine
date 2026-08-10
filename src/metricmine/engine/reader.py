"""Contract loading, JSON Schema validation, and cross-checks (spec §5).

The reader is the engine's static groundedness, all fail-closed: the JSON
Schema rejects shape violations (including quality rules, dead letters per
F-12, and reserved category names), and the cross-checks below hold the
mapping contract to the silver contract it maps. jsonschema comes from the
dev dependency group — regeneration is a dev workflow, never a runtime one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import jsonschema
import yaml

from metricmine.profiling.writer import latest_version

# Every emitted model carries one of these prefixes or the reserved name,
# so a category name matching them could collide with a model name — the
# loud gate-3 failure F-12 probed. The JSON Schema rejects them first;
# this re-check is defense in depth.
_RESERVED_PREFIXES = ("dim_", "fact_", "vw_", "silver_", "bronze_", "stg_")
_RESERVED_NAMES = ("context_registry",)


class EngineContractError(ValueError):
    """A mapping contract failed schema validation or a cross-check."""


@dataclass(frozen=True)
class EngineInputs:
    mapping: dict
    star: dict
    silver: dict
    json_schema: dict


def load_inputs(repo_root: Path) -> EngineInputs:
    """Load the engine's inputs per the engine: block of config/default.yaml."""
    config_path = Path(repo_root) / "config" / "default.yaml"
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))["engine"]

    def _yaml(key: str) -> dict:
        return yaml.safe_load(
            (Path(repo_root) / cfg[key]).read_text(encoding="utf-8")
        )

    return EngineInputs(
        mapping=_yaml("mapping_contract"),
        star=_yaml("gold_contract"),
        silver=_yaml("silver_contract"),
        json_schema=json.loads(
            (Path(repo_root) / cfg["schema_path"]).read_text(encoding="utf-8")
        ),
    )


def load_compiled_context(repo_root: Path) -> tuple[str, dict]:
    """The newest committed compiled-context artifact, fail-closed (D-30).

    Resolves the context: block of config/default.yaml, picks the newest
    vNNNN, and refuses an artifact whose cited contract versions diverge
    from the loaded contracts — the registry must never embed stale
    context.
    """
    config_path = Path(repo_root) / "config" / "default.yaml"
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    compiled_dir = Path(repo_root) / cfg["context"]["output_dir"]
    current = latest_version(compiled_dir)
    if not current:
        raise EngineContractError(
            "no compiled-context artifact under context/compiled/;"
            " run `make context` first (D-30)"
        )
    version = f"v{current:04d}"
    parsed = json.loads(
        (compiled_dir / f"{version}.json").read_text(encoding="utf-8")
    )
    inputs = load_inputs(repo_root)
    declared = {
        "gold_contract": inputs.star["version"],
        "mapping_contract": inputs.mapping["version"],
        "silver_contract": inputs.silver["version"],
    }
    for key, expected in declared.items():
        cited = parsed["sources"][key]["version"]
        if cited != expected:
            raise EngineContractError(
                f"compiled-context artifact {version} is stale:"
                f" sources.{key} is {cited}, contracts say {expected};"
                " run `make context` (D-30)"
            )
    return version, parsed


def validate_mapping(mapping: dict, silver: dict, json_schema: dict) -> None:
    """Validate the mapping contract, fail-closed (spec §5).

    JSON Schema first, then every cross-check against the silver contract.
    Raises EngineContractError on the first violation; the engine emits
    nothing after any failure.
    """
    try:
        jsonschema.validate(instance=mapping, schema=json_schema)
    except jsonschema.ValidationError as exc:
        raise EngineContractError(
            f"mapping contract violates the JSON Schema: {exc.message}"
        ) from exc

    category = mapping["schema"][0]
    name = category["name"]
    if name in _RESERVED_NAMES or name.startswith(_RESERVED_PREFIXES):
        raise EngineContractError(
            f"category name {name!r} matches a reserved model-name pattern"
            " (F-12 collision guard)"
        )

    silver_object = silver["schema"][0]
    expected_source = f"silver.{silver_object['name']}"
    if category["sourceTable"] != expected_source:
        raise EngineContractError(
            f"sourceTable {category['sourceTable']!r} does not name the"
            f" silver contract's object ({expected_source!r})"
        )

    silver_columns = {prop["name"] for prop in silver_object["properties"]}
    declared = {prop["name"] for prop in category["properties"]}
    for prop in category["properties"]:
        if prop["name"] not in silver_columns:
            raise EngineContractError(
                f"mapped field {prop['name']!r} does not exist in the"
                " silver contract"
            )

    time_fields = [
        prop["name"]
        for prop in category["properties"]
        if prop["mappingRole"] == "time"
    ]
    if time_fields != [category["timeColumn"]]:
        raise EngineContractError(
            f"timeColumn {category['timeColumn']!r} must be declared with"
            f" mappingRole time and be the only time-role field"
            f" (time-role fields: {time_fields})"
        )

    grain = category["grain"]
    grain_refs: list[str] = []
    if grain["type"] == "transaction":
        for identifier in grain["degenerateIdentifiers"]:
            if identifier["source"] == "column":
                grain_refs.append(identifier["column"])
            else:
                grain_refs.extend(identifier["of"])
    else:
        grain_refs.extend(grain["aggregations"])
    for ref in grain_refs:
        if ref not in declared:
            raise EngineContractError(
                f"grain reference {ref!r} does not name a declared field"
            )

    for prop in category["properties"]:
        if prop["mappingRole"] == "measure" and prop["logicalType"] not in (
            "integer",
            "number",
        ):
            raise EngineContractError(
                f"measure {prop['name']!r} has non-numeric logicalType"
                f" {prop['logicalType']!r}"
            )
