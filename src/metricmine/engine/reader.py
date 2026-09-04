"""Contract loading, JSON Schema validation, and cross-checks (spec §5).

The reader is the engine's static groundedness, all fail-closed: the JSON
Schema rejects shape violations (including quality rules, dead letters per
F-12, and reserved category names), and the cross-checks below hold each
mapping contract to the silver contract it maps. jsonschema comes from the
dev dependency group; regeneration is a dev workflow, never a runtime one.

Since the multi-source fan-in (Arc 6, D-41; D-29 as amended) the engine
block lists ``mapping_contracts`` (one per category; the singular
``mapping_contract`` key is still accepted as a one-element list). Each
mapping's silver contract resolves by convention from its ``sourceTable``:
``silver.<table>`` maps to ``contracts/<table>.odcs.yaml``, the table
contract whose ``id`` is the table name. The star-level cross-checks
(unique category names, unique source tables, a ``captured_at`` column on
every mapped silver table) run over the whole set before anything emits.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import jsonschema
import yaml

from metricmine.profiling.writer import latest_version

# Every emitted model carries one of these prefixes or the reserved name,
# so a category name matching them could collide with a model name: the
# loud gate-3 failure F-12 probed. The JSON Schema rejects them first;
# this re-check is defense in depth.
_RESERVED_PREFIXES = ("dim_", "fact_", "vw_", "mart_", "silver_", "bronze_", "stg_")
_RESERVED_NAMES = ("context_registry",)

# The capture watermark every mapped silver table carries (D-38): the
# emitted models read it unconditionally, so its absence is a reader
# error, never a build-time surprise.
CAPTURE_COLUMN = "captured_at"


class EngineContractError(ValueError):
    """A mapping contract failed schema validation or a cross-check."""


@dataclass(frozen=True)
class EngineInputs:
    mappings: list[dict]
    star: dict
    silvers: dict[str, dict]
    json_schema: dict

    @property
    def mapping(self) -> dict:
        """The single mapping contract, for one-category callers.

        Raises when the engine block lists more than one category; such
        callers iterate ``mappings`` instead.
        """
        if len(self.mappings) != 1:
            raise EngineContractError(
                "EngineInputs.mapping is defined for a one-category engine"
                f" block; this block lists {len(self.mappings)} mapping"
                " contracts, iterate .mappings"
            )
        return self.mappings[0]

    @property
    def silver(self) -> dict:
        """The single silver contract, for one-category callers."""
        return self.silvers[_silver_table(self.mapping)]


def _silver_table(mapping: dict) -> str:
    return mapping["schema"][0]["sourceTable"].split(".", 1)[1]


def mapping_contract_paths(cfg: dict) -> list[str]:
    """The engine block's mapping contract list, fail-closed.

    ``mapping_contracts`` (a non-empty list) is the form since the
    fan-in; ``mapping_contract`` (one path) reads as a one-element list
    so a pre-fan-in config keeps working. Both keys at once, or neither,
    is a config error.
    """
    plural = cfg.get("mapping_contracts")
    singular = cfg.get("mapping_contract")
    if plural is not None and singular is not None:
        raise EngineContractError(
            "engine block names both mapping_contracts and mapping_contract;"
            " keep the list only"
        )
    if plural is not None:
        if not isinstance(plural, list) or not plural:
            raise EngineContractError(
                "engine.mapping_contracts must be a non-empty list of paths"
            )
        return [str(path) for path in plural]
    if singular is None:
        raise EngineContractError(
            "engine block names no mapping contract (mapping_contracts)"
        )
    return [str(singular)]


def load_inputs(repo_root: Path) -> EngineInputs:
    """Load the engine's inputs per the engine: block of config/default.yaml."""
    config_path = Path(repo_root) / "config" / "default.yaml"
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))["engine"]

    def _yaml(rel_path: str) -> dict:
        return yaml.safe_load(
            (Path(repo_root) / rel_path).read_text(encoding="utf-8")
        )

    mappings = [_yaml(path) for path in mapping_contract_paths(cfg)]
    silvers: dict[str, dict] = {}
    for mapping in mappings:
        table = _silver_table(mapping)
        silver_path = Path(repo_root) / "contracts" / f"{table}.odcs.yaml"
        if not silver_path.is_file():
            raise EngineContractError(
                f"mapping contract {mapping.get('id')!r} names sourceTable"
                f" silver.{table} but contracts/{table}.odcs.yaml does not"
                " exist"
            )
        silvers[table] = yaml.safe_load(silver_path.read_text(encoding="utf-8"))
    return EngineInputs(
        mappings=mappings,
        star=_yaml(cfg["gold_contract"]),
        silvers=silvers,
        json_schema=json.loads(
            (Path(repo_root) / cfg["schema_path"]).read_text(encoding="utf-8")
        ),
    )


def validate_inputs(inputs: EngineInputs) -> None:
    """Every mapping against its silver contract, then the star-level
    cross-checks over the set (spec §5 as amended), fail-closed."""
    for mapping in inputs.mappings:
        table = _silver_table(mapping)
        validate_mapping(mapping, inputs.silvers[table], inputs.json_schema)
    names = [mapping["schema"][0]["name"] for mapping in inputs.mappings]
    if len(set(names)) != len(names):
        raise EngineContractError(
            f"category names must be unique across mapping contracts: {names}"
        )
    tables = [mapping["schema"][0]["sourceTable"] for mapping in inputs.mappings]
    if len(set(tables)) != len(tables):
        raise EngineContractError(
            "each silver table maps into one category; duplicate"
            f" sourceTable: {tables}"
        )


def load_compiled_context(repo_root: Path) -> tuple[str, dict]:
    """The newest committed compiled-context artifact, fail-closed (D-30).

    Resolves the context: block of config/default.yaml, picks the newest
    vNNNN, and refuses an artifact whose cited contract versions diverge
    from the loaded contracts; the registry must never embed stale
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
    expected = compiled_sources(inputs)
    cited = parsed["sources"]

    def _id_version(entry: dict | None) -> dict | None:
        if entry is None:
            return None
        return {"id": entry.get("id"), "version": entry.get("version")}

    def _id_versions(entries: list | None) -> list | None:
        if entries is None:
            return None
        return [_id_version(entry) for entry in entries]

    stale = []
    if _id_version(cited.get("gold_contract")) != expected["gold_contract"]:
        stale.append("gold_contract")
    if _id_versions(cited.get("mapping_contracts")) != expected["mapping_contracts"]:
        stale.append("mapping_contracts")
    if _id_versions(cited.get("silver_contracts")) != expected["silver_contracts"]:
        stale.append("silver_contracts")
    if stale:
        raise EngineContractError(
            f"compiled-context artifact {version} is stale on"
            f" {', '.join(stale)}; the contracts on disk differ from the"
            " ones it cites; run `make context` (D-30)"
        )
    return version, parsed


def compiled_sources(inputs: EngineInputs) -> dict:
    """The sources block a current compiled-context artifact must cite:
    the star contract, then every mapping and every silver contract in
    category order, each as id plus version."""
    ordered = sorted(inputs.mappings, key=lambda m: m["schema"][0]["name"])
    return {
        "gold_contract": {
            "id": inputs.star["id"],
            "version": inputs.star["version"],
        },
        "mapping_contracts": [
            {"id": mapping["id"], "version": mapping["version"]}
            for mapping in ordered
        ],
        "silver_contracts": [
            {
                "id": inputs.silvers[_silver_table(mapping)]["id"],
                "version": inputs.silvers[_silver_table(mapping)]["version"],
            }
            for mapping in ordered
        ],
    }


def validate_mapping(mapping: dict, silver: dict, json_schema: dict) -> None:
    """Validate one mapping contract, fail-closed (spec §5).

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
    if CAPTURE_COLUMN not in silver_columns:
        raise EngineContractError(
            f"silver contract {silver.get('id')!r} declares no"
            f" {CAPTURE_COLUMN} column; every mapped silver table carries"
            " the capture watermark (D-38)"
        )
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
