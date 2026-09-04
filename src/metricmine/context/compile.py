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

Every entry keeps two things apart, by name, so an agent can tell them
apart (Amendment W to D-31): ``data`` is what the columns ARE (the types
and roles, the grain, the conformed keys and which other categories share
them, the typed surface), derived from the contracts' typed declarations;
``expert_context`` is what people WROTE about them in the human-owned
silver contract, the mapping contract, and the star contract (the
subject, how to read it, the limitations, the lineage and vintage, the
declared joins with their measured completeness, the cross-category
joins, the decisions, and the two descriptions each field carries). The
expert context is authored knowledge, never a measurement; the ``note``
inside it says so. The top-level ``role`` and ``manifest`` stay where
get_schema has always read them.
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

EXPERT_CONTEXT_NOTE = (
    "Authored knowledge, not a measurement: what the people who approved the "
    "governing contracts wrote about this data (the silver contract that "
    "settled the table, the mapping contract that declared the category, "
    "the star contract that governs the container). Units, vintages, what "
    "a null means, which joins hold and how completely, and the decisions "
    "taken in silver live here. The data section beside it is derived from "
    "the contracts' typed declarations; the rows in the warehouse are the "
    "measurement. Where a claim here and the data disagree, the data is the "
    "fact and this is the claim to check."
)

DECISION_PREFIX = "decision"

# Silver custom properties that carry authored prose or structure into
# the expert context, with the label each takes there.
_SILVER_CONTEXT_KEYS = (
    ("sourceLineage", "lineage"),
    ("vintage", "vintage"),
    ("joins", "joins"),
)

# The star's structured custom properties (Amendment W): a list of the
# cross-category joins the typed surfaces support, each measured.
CROSS_CATEGORY_JOINS = "crossCategoryJoins"

# What a string value looks like on the served surface (D-18 as amended
# by Amendment M): the typed columns are projected from the canonical
# payload, so text is lowercase there whatever case silver carries. An
# agent that writes origin_airport = 'JFK' gets no rows; this says so
# where the agent reads.
VALUE_FORM = (
    "String columns on the typed surface carry canonical lowercase text"
    " (D-18 as amended): write string literals in lowercase (carrier_code"
    " = 'ev', origin_airport = 'jfk'), or compare with lower(). Numbers,"
    " dates, and timestamps are typed and unaffected."
)


def _harvest(prop: dict) -> dict:
    """One field's data shape: the typed declaration, nothing prose."""
    return {
        "logicalType": prop["logicalType"],
        "mappingRole": prop["mappingRole"],
        "physicalType": prop["physicalType"],
        "required": bool(prop.get("required", False)),
    }


def _custom_properties(contract: dict) -> dict:
    return {
        entry["property"]: entry["value"]
        for entry in contract.get("customProperties", [])
    }


def _text(value) -> str:
    return str(value or "").strip()


def _decisions(*contracts: dict) -> dict[str, str]:
    """Every decision* custom property across the given contracts, in
    contract order; a later contract's key wins, which never happens for
    a silver and its mapping (their decision keys are disjoint by
    convention: silver records cleanup decisions, the mapping records
    modeling decisions)."""
    out: dict[str, str] = {}
    for contract in contracts:
        for key, value in _custom_properties(contract).items():
            if key.startswith(DECISION_PREFIX):
                out[key] = _text(value)
    return out


def _structured_or_text(value):
    """A custom property value as written: a list or mapping passes
    through (structured joins), anything else becomes stripped text."""
    if isinstance(value, (list, dict)):
        return value
    return _text(value)


def _silver_descriptions(silver: dict) -> dict[str, str]:
    obj = silver["schema"][0]
    return {
        str(prop["name"]): _text(prop.get("description"))
        for prop in obj.get("properties", [])
    }


def _cross_category_joins(star: dict, category: str | None = None) -> list[dict]:
    """The star's declared cross-category joins, every one or only those
    a category takes part in."""
    raw = _custom_properties(star).get(CROSS_CATEGORY_JOINS)
    joins = list(raw) if isinstance(raw, list) else []
    if category is None:
        return joins
    return [
        join
        for join in joins
        if category in (join.get("left"), join.get("right"))
    ]


def _fields_context(names: list[str], properties: dict, silver_fields: dict[str, str]) -> dict:
    """Each field's two descriptions: the mapping's meaning within the
    category, and the silver column's own where it says something
    different."""
    fields = {}
    for name in names:
        entry = {"meaning": _text(properties[name].get("description"))}
        source_meaning = silver_fields.get(name, "")
        if source_meaning and source_meaning != entry["meaning"]:
            entry["source_meaning"] = source_meaning
        fields[name] = entry
    return fields


def _expert_context(
    silver: dict, mapping: dict, star: dict, category: str, names: list[str], properties: dict
) -> dict:
    """What people wrote about a category: the silver contract's subject,
    usage, and limitations, its lineage and vintage and declared joins,
    the star's cross-category joins this category takes part in, the
    decision record of both contracts, and each field's descriptions."""
    custom = _custom_properties(silver)
    description = silver.get("description") or {}
    mapping_description = mapping.get("description") or {}
    context = {
        "note": EXPERT_CONTEXT_NOTE,
        "subject": _text(description.get("purpose")),
        "how_to_read": _text(description.get("usage")),
        "limitations": _text(description.get("limitations")),
        "category_purpose": _text(mapping_description.get("purpose")),
        "category_usage": _text(mapping_description.get("usage")),
        "category_limitations": _text(mapping_description.get("limitations")),
        "governing_contracts": {
            "silver": f"{silver['id']} v{silver['version']}",
            "mapping": f"{mapping['id']} v{mapping['version']}",
            "star": f"{star['id']} v{star['version']}",
        },
        "fields": _fields_context(names, properties, _silver_descriptions(silver)),
    }
    for key, label in _SILVER_CONTEXT_KEYS:
        if key in custom:
            context[label] = _structured_or_text(custom[key])
    cross = _cross_category_joins(star, category)
    if cross:
        context["cross_category_joins"] = cross
    decisions = _decisions(silver, mapping)
    if decisions:
        context["decisions"] = decisions
    return context


def _where_to_query(category: str, typed_surface: str, source_table: str) -> str:
    """One sentence an agent acts on: the served surface for this category.
    The expert context speaks of the silver table it was written for;
    the served database carries gold only (D-31), so the pointer says
    where the same rows are answered from."""
    return (
        f"gold.{typed_surface}: one typed row per {category} event, the served"
        f" surface for this category. The silver table the expert context"
        f" names ({source_table}) is its source and is not served; the star"
        f" tables are the provenance layer."
    )


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


def _conformed_rules(star: dict) -> dict[str, dict]:
    """The star contract's `conformedKeyRules` (`key=TYPE:regex; ...`)."""
    raw = str(_custom_properties(star).get("conformedKeyRules", "")).strip()
    rules: dict[str, dict] = {}
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        key, _, rest = entry.partition("=")
        physical, _, regex = rest.partition(":")
        rules[key.strip()] = {"physicalType": physical.strip(), "rule": regex.strip()}
    return rules


def _shared_key_map(star: StarEmission, inputs) -> dict[str, dict[str, list[str]]]:
    """key -> {category: [columns]} across every category, so each entry
    can say which other categories share a conformed key."""
    out: dict[str, dict[str, list[str]]] = {}
    for emission in star.categories:
        silver = inputs.silvers[emission.source_model]
        mapped = {p["name"] for p in emission.category["properties"]}
        for column, key in _conformed_keys(silver, mapped).items():
            out.setdefault(key, {}).setdefault(emission.category_name, []).append(column)
    return out


def _category_entries(
    repo_root: Path,
    emission: Emission,
    silver: dict,
    rules: dict[str, dict],
    shared: dict[str, dict[str, list[str]]],
) -> list[dict]:
    """The two entries a mapping contract owns: its dimensions manifest
    and its measures manifest, both citing the mapping. Each carries the
    data section (typed declarations) and the expert context (authored
    prose), kept apart by name."""
    mapping = emission.mapping
    star = emission.star
    category = emission.category_name
    properties = {p["name"]: p for p in emission.category["properties"]}
    typed_surface = _typed_surface(repo_root, category)
    group = emission.category["entityGroup"]
    conformed = {}
    for column, key in _conformed_keys(silver, set(properties)).items():
        others = {
            other: columns
            for other, columns in shared.get(key, {}).items()
            if other != category
        }
        conformed[column] = {
            "key": key,
            "nullable": not bool(properties[column].get("required", False)),
            "shared_with": others,
            **rules.get(key, {}),
        }
    grain = emission.category["grain"]
    grain_keys = [
        identifier.get("of", [])
        for identifier in grain.get("degenerateIdentifiers", [])
    ]

    def entry(schema_key: str, compiled: dict) -> dict:
        return {
            "schema_key": schema_key,
            "entity_group": group,
            "contract_name": mapping["id"],
            "contract_version": mapping["version"],
            "compiled_context": compiled,
        }

    dim_names = list(emission.dim_payload_columns)
    measure_names = list(emission.measure_manifest)
    return [
        entry(
            emission.dim_col_key,
            {
                "category": category,
                "role": "dimensions",
                "manifest": emission.dim_manifest,
                "data": {
                    "conformed_keys": conformed,
                    "derived_identifiers": {
                        identifier["name"]: {
                            "derivation": identifier["derivation"],
                            "of": identifier["of"],
                            "source": identifier["source"],
                        }
                        for identifier in emission.derived_identifiers
                    },
                    "fields": {name: _harvest(properties[name]) for name in dim_names},
                    "grain": {"type": grain["type"], "keys": grain_keys[0] if grain_keys else []},
                    "source_table": emission.source_table,
                    "time_column": emission.time_column,
                    "time_grain": emission.time_grain,
                    "typed_surface": typed_surface,
                    "value_form": VALUE_FORM,
                    "where_to_query": _where_to_query(category, typed_surface, emission.source_table),
                },
                "expert_context": _expert_context(
                    silver, mapping, star, category, dim_names + [emission.time_column], properties
                ),
            },
        ),
        entry(
            emission.fact_col_key,
            {
                "category": category,
                "role": "measures",
                "manifest": emission.measure_manifest,
                "data": {
                    "fields": {name: _harvest(properties[name]) for name in measure_names},
                    "source_table": emission.source_table,
                    "typed_surface": typed_surface,
                    "value_form": VALUE_FORM,
                    "where_to_query": _where_to_query(category, typed_surface, emission.source_table),
                },
                "expert_context": _expert_context(
                    silver, mapping, star, category, measure_names, properties
                ),
            },
        ),
    ]


def _star_context(star: dict, subject: str, how_to_read: str, **extra) -> dict:
    """The expert context of a shared group: the star contract's own
    purpose, usage, and limitations frame every shared object, and each
    group adds what people wrote about it."""
    description = star.get("description") or {}
    context = {
        "note": EXPERT_CONTEXT_NOTE,
        "subject": subject,
        "how_to_read": how_to_read,
        "star_purpose": _text(description.get("purpose")),
        "star_usage": _text(description.get("usage")),
        "star_limitations": _text(description.get("limitations")),
        "governing_contracts": {"star": f"{star['id']} v{star['version']}"},
    }
    context.update(extra)
    return context


def _shared_entries(star: StarEmission, inputs) -> list[dict]:
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

    def silver_of(emission: Emission) -> dict:
        return inputs.silvers[emission.source_model]

    def time_property(emission: Emission) -> dict:
        return next(
            p
            for p in emission.category["properties"]
            if p["name"] == emission.time_column
        )

    sources_context = {}
    for emission in star.categories:
        silver = silver_of(emission)
        custom = _custom_properties(silver)
        sources_context[emission.source_table] = {
            "category": emission.category_name,
            "subject": _text((silver.get("description") or {}).get("purpose")),
            "governing_contracts": {
                "silver": f"{silver['id']} v{silver['version']}",
                "mapping": f"{emission.mapping['id']} v{emission.mapping['version']}",
            },
            **{
                label: _structured_or_text(custom[key])
                for key, label in _SILVER_CONTEXT_KEYS
                if key in custom and label != "joins"
            },
        }

    timeframe_context = {
        emission.category_name: {
            "time_column_meaning": _text(time_property(emission).get("description")),
            "vintage": _text(_custom_properties(silver_of(emission)).get("vintage")),
        }
        for emission in star.categories
    }
    cross = _cross_category_joins(contract)

    return [
        entry(
            star.source_col_key,
            "source",
            {
                "role": "source",
                "manifest": star.source_manifest,
                "data": {
                    "fields": {
                        "source_table": {
                            "logicalType": "string",
                            "physicalType": "VARCHAR",
                            "required": True,
                        }
                    },
                    "source_tables": [
                        emission.source_table for emission in star.categories
                    ],
                },
                "expert_context": _star_context(
                    contract,
                    subject=(
                        "The source group: one row per silver table the star is"
                        " built from, named as schema.table. Every fact row"
                        " carries the source hash of the table it came from."
                    ),
                    how_to_read=(
                        "Resolve a fact's source_hash_id here to learn which"
                        " silver table minted it, then read that table's"
                        " subject below; the category's own registry entries"
                        " carry the full expert context."
                    ),
                    fields={
                        "source_table": {
                            "meaning": (
                                "The silver table the fact row was built from,"
                                " as schema.table; its subject and governing"
                                " contracts are listed under sources."
                            )
                        }
                    },
                    sources=sources_context,
                ),
            },
        ),
        # No values harvest for run: the run dim carries build-time
        # lineage; the registry describes meaning.
        entry(
            star.run_col_key,
            "run",
            {
                "role": "run",
                "manifest": star.run_manifest,
                "data": {
                    "fields": {
                        name: {
                            "logicalType": "string",
                            "physicalType": "VARCHAR",
                            "required": True,
                        }
                        for name in star.run_manifest
                    }
                },
                "expert_context": _star_context(
                    contract,
                    subject=(
                        "The run group: build lineage, one row per mapping"
                        " contract version and engine version that minted"
                        " fact rows. An audit attribute, never an analytical"
                        " one."
                    ),
                    how_to_read=(
                        "run_hash_id on a fact row is a non-key attribute"
                        " (rule 14): resolve it here to see which mapping"
                        " contract version and engine version built the row."
                        " Equal facts rebuilt under a new engine keep their"
                        " keys and change only this attribute."
                    ),
                    fields={
                        "mapping_contract_name": {
                            "meaning": "The id of the mapping contract whose approval created the category's keys."
                        },
                        "mapping_contract_version": {
                            "meaning": "That mapping contract's version at build time."
                        },
                        "engine_version": {
                            "meaning": "The auto-modeling engine version that emitted the models (D-07)."
                        },
                    },
                ),
            },
        ),
        entry(
            star.timeframe_col_key,
            "timeframe",
            {
                "role": "timeframe",
                "manifest": star.timeframe_manifest,
                "data": {
                    "categories": {
                        emission.category_name: {
                            "time_column": emission.time_column,
                            "time_grain": emission.time_grain,
                            "field": _harvest(time_property(emission)),
                        }
                        for emission in star.categories
                    },
                    "fields": {
                        "grain": {
                            "logicalType": "string",
                            "physicalType": "VARCHAR",
                            "required": True,
                        },
                        "period_start": {
                            "logicalType": "date",
                            "physicalType": "TIMESTAMP",
                            "required": True,
                        },
                    },
                },
                "expert_context": _star_context(
                    contract,
                    subject=(
                        "The conformed calendar (D-17 Amendment R): one"
                        " timeframe manifest for the whole star, so equal"
                        " periods at equal grain are one row whichever"
                        " category minted them."
                    ),
                    how_to_read=(
                        "Two categories share a calendar row only at the same"
                        " grain: an hour-grain category and a minute-grain"
                        " category never share rows, and their windows may"
                        " not overlap at all. Compare windows and grains per"
                        " category below before joining on timeframe_hash_id;"
                        " for analytical joins prefer the typed surfaces and"
                        " the cross-category joins the star declares."
                    ),
                    fields={
                        "grain": {
                            "meaning": (
                                "The declared time grain of the category the"
                                " period belongs to (minute, hour, day, week,"
                                " month, quarter, year)."
                            )
                        },
                        "period_start": {
                            "meaning": (
                                "The category's declared time column truncated"
                                " to its grain and rendered canonically; equal"
                                " periods at equal grain hash to one row"
                                " whichever category minted them (the conformed"
                                " calendar, D-17 Amendment R)."
                            )
                        },
                    },
                    categories=timeframe_context,
                    **({"cross_category_joins": cross} if cross else {}),
                ),
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

    entries = _shared_entries(star, inputs)
    rules = _conformed_rules(inputs.star)
    shared = _shared_key_map(star, inputs)
    for emission in star.categories:
        silver = inputs.silvers[emission.source_model]
        entries.extend(_category_entries(repo_root, emission, silver, rules, shared))

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
