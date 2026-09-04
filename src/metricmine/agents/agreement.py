"""The first-class agreement metric for the describe stance (D-25, D-35).

Scores a rendered describe draft against an oracle contract on the
elements the profile can evidence, and nothing else: per-column
logicalType, physicalType, required, primaryKey, and primaryKeyPosition;
column presence and ordinal order; the grain tuple; and quality-rule
type shapes. Prose, examples, custom properties, status, and version are
deliberately unscored: the profile cannot settle them, so agreement over
them would be a claim without evidence. The result is an n=1 study
against self-authored ground truth, reported as such, never as accuracy.
"""

from __future__ import annotations

_COLUMN_FIELDS = (
    "logicalType",
    "physicalType",
    "required",
    "primaryKey",
    "primaryKeyPosition",
)


def _column_index(document: dict) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for prop in document["schema"][0]["properties"]:
        index[prop["name"]] = {
            "logicalType": prop.get("logicalType"),
            "physicalType": prop.get("physicalType"),
            "required": prop.get("required"),
            # Absent reads False: an unflagged column is not a key.
            "primaryKey": bool(prop.get("primaryKey", False)),
            "primaryKeyPosition": prop.get("primaryKeyPosition"),
        }
    return index


def _grain(document: dict) -> list[str]:
    keyed = [
        prop
        for prop in document["schema"][0]["properties"]
        if prop.get("primaryKey")
    ]
    return [
        prop["name"]
        for prop in sorted(keyed, key=lambda p: p["primaryKeyPosition"])
    ]


def _rule_types(node: dict) -> list[str]:
    types: list[str] = []
    for rule in node.get("quality") or []:
        if rule["type"] == "library":
            types.append(f"library:{rule.get('metric')}")
        else:
            types.append(rule["type"])
    return types


def score(draft: dict, oracle: dict) -> dict:
    """First-class agreement between a draft and an oracle document."""
    draft_cols = _column_index(draft)
    oracle_cols = _column_index(oracle)
    shared = [name for name in oracle_cols if name in draft_cols]
    mismatches: list[str] = []
    field_agree = dict.fromkeys(_COLUMN_FIELDS, 0)
    for name in oracle_cols:
        if name not in draft_cols:
            mismatches.append(f"{name}: missing from the draft")
    for name in draft_cols:
        if name not in oracle_cols:
            mismatches.append(f"{name}: extra in the draft")
    for name in shared:
        for field in _COLUMN_FIELDS:
            want = oracle_cols[name][field]
            got = draft_cols[name][field]
            if want == got:
                field_agree[field] += 1
            else:
                mismatches.append(
                    f"{name}.{field}: oracle={want!r} draft={got!r}"
                )

    oracle_grain = _grain(oracle)
    draft_grain = _grain(draft)
    oracle_table = oracle["schema"][0]
    draft_table = draft["schema"][0]
    oracle_column_rules = {
        prop["name"]: _rule_types(prop)
        for prop in oracle_table["properties"]
        if prop.get("quality")
    }
    draft_column_rules = {
        prop["name"]: _rule_types(prop)
        for prop in draft_table["properties"]
        if prop.get("quality")
    }
    table_oracle = _rule_types(oracle_table)
    table_draft = _rule_types(draft_table)
    return {
        "oracle_id": oracle.get("id"),
        "columns": {
            "oracle": len(oracle_cols),
            "draft": len(draft_cols),
            "shared": len(shared),
            "ordinal_order_equal": list(oracle_cols) == list(draft_cols),
        },
        "first_class_checks": {
            "agree": sum(field_agree.values()),
            "checked": len(shared) * len(_COLUMN_FIELDS),
            "per_field": {
                field: f"{field_agree[field]}/{len(shared)}"
                for field in _COLUMN_FIELDS
            },
        },
        "grain": {
            "oracle": oracle_grain,
            "draft": draft_grain,
            "set_equal": set(oracle_grain) == set(draft_grain),
            "order_equal": oracle_grain == draft_grain,
        },
        "rule_types": {
            "table_oracle": table_oracle,
            "table_draft": table_draft,
            "table_equal": table_oracle == table_draft,
            "column_equal": oracle_column_rules == draft_column_rules,
        },
        "mismatches": mismatches,
    }


def summary_lines(result: dict) -> list[str]:
    """Terminal lines for the agreement block: one study, no averages."""
    first = result["first_class_checks"]
    grain = result["grain"]
    rules = result["rule_types"]
    lines = [
        f"agreement study (n=1) against oracle {result['oracle_id']!r}: "
        f"first-class {first['agree']}/{first['checked']} agree",
        "  per field: "
        + ", ".join(
            f"{field} {ratio}" for field, ratio in first["per_field"].items()
        ),
        f"  columns: oracle {result['columns']['oracle']}, draft "
        f"{result['columns']['draft']}, ordinal order equal: "
        f"{result['columns']['ordinal_order_equal']}",
        f"  grain: set equal {grain['set_equal']}, order equal "
        f"{grain['order_equal']} (oracle {grain['oracle']}, draft "
        f"{grain['draft']})",
        f"  rule types: table equal {rules['table_equal']}, column equal "
        f"{rules['column_equal']}",
    ]
    if result["mismatches"]:
        lines.append("  mismatches:")
        lines.extend(f"    - {item}" for item in result["mismatches"])
    else:
        lines.append("  mismatches: none")
    return lines


# ---------------------------------------------------------------- mapping
# The propose stance's study (D-41): a rendered mapping draft against the
# committed, human-authored mapping contract. Scored on what the silver
# profile can evidence: per property the mappingRole, logicalType,
# physicalType, and required flag; property presence and order; the
# category header (entityGroup, sourceTable, timeColumn, timeGrain, grain
# type); and the degenerate identifiers as declared. Descriptions and
# decisions stay unscored, as above.

_MAPPING_FIELDS = ("mappingRole", "logicalType", "physicalType", "required")


def _mapping_index(document: dict) -> dict[str, dict]:
    return {
        prop["name"]: {
            "mappingRole": prop.get("mappingRole"),
            "logicalType": prop.get("logicalType"),
            "physicalType": prop.get("physicalType"),
            "required": bool(prop.get("required", False)),
        }
        for prop in document["schema"][0]["properties"]
    }


def _identifiers(document: dict) -> list[tuple]:
    grain = document["schema"][0].get("grain") or {}
    out = []
    for entry in grain.get("degenerateIdentifiers") or []:
        if entry.get("source") == "derived":
            out.append(("derived", entry.get("name"), entry.get("derivation"), tuple(entry.get("of") or [])))
        else:
            out.append(("column", entry.get("column")))
    return out


def score_mapping(draft: dict, oracle: dict) -> dict:
    """First-class agreement between a mapping draft and its oracle."""
    draft_props = _mapping_index(draft)
    oracle_props = _mapping_index(oracle)
    shared = [name for name in oracle_props if name in draft_props]
    mismatches: list[str] = []
    field_agree = dict.fromkeys(_MAPPING_FIELDS, 0)
    for name in oracle_props:
        if name not in draft_props:
            mismatches.append(f"{name}: missing from the draft")
    for name in draft_props:
        if name not in oracle_props:
            mismatches.append(f"{name}: extra in the draft")
    for name in shared:
        for field in _MAPPING_FIELDS:
            want = oracle_props[name][field]
            got = draft_props[name][field]
            if want == got:
                field_agree[field] += 1
            else:
                mismatches.append(f"{name}.{field}: oracle={want!r} draft={got!r}")

    oracle_cat = oracle["schema"][0]
    draft_cat = draft["schema"][0]
    header = {}
    for key in ("entityGroup", "sourceTable", "timeColumn", "timeGrain"):
        header[key] = oracle_cat.get(key) == draft_cat.get(key)
        if not header[key]:
            mismatches.append(f"{key}: oracle={oracle_cat.get(key)!r} draft={draft_cat.get(key)!r}")
    oracle_grain_type = (oracle_cat.get("grain") or {}).get("type")
    draft_grain_type = (draft_cat.get("grain") or {}).get("type")
    header["grainType"] = oracle_grain_type == draft_grain_type
    if not header["grainType"]:
        mismatches.append(f"grain.type: oracle={oracle_grain_type!r} draft={draft_grain_type!r}")
    oracle_ids = _identifiers(oracle)
    draft_ids = _identifiers(draft)
    ids_equal = oracle_ids == draft_ids
    if not ids_equal:
        mismatches.append(f"degenerateIdentifiers: oracle={oracle_ids!r} draft={draft_ids!r}")

    def roles(index: dict, role: str) -> list[str]:
        return [name for name, spec in index.items() if spec["mappingRole"] == role]

    return {
        "oracle_id": oracle.get("id"),
        "properties": {
            "oracle": len(oracle_props),
            "draft": len(draft_props),
            "shared": len(shared),
            "ordinal_order_equal": list(oracle_props) == list(draft_props),
        },
        "first_class_checks": {
            "agree": sum(field_agree.values()),
            "checked": len(shared) * len(_MAPPING_FIELDS),
            "per_field": {
                field: f"{field_agree[field]}/{len(shared)}" for field in _MAPPING_FIELDS
            },
        },
        "header": header,
        "roles": {
            "dimensions_equal": set(roles(oracle_props, "dimension")) == set(roles(draft_props, "dimension")),
            "measures_equal": set(roles(oracle_props, "measure")) == set(roles(draft_props, "measure")),
        },
        "identifiers_equal": ids_equal,
        "mismatches": mismatches,
    }


def summary_lines_mapping(result: dict) -> list[str]:
    first = result["first_class_checks"]
    header = result["header"]
    lines = [
        f"agreement study (n=1) against oracle {result['oracle_id']!r}: "
        f"first-class {first['agree']}/{first['checked']} agree",
        "  per field: "
        + ", ".join(f"{field} {ratio}" for field, ratio in first["per_field"].items()),
        f"  properties: oracle {result['properties']['oracle']}, draft "
        f"{result['properties']['draft']}, ordinal order equal: "
        f"{result['properties']['ordinal_order_equal']}",
        "  header: " + ", ".join(f"{key} {value}" for key, value in header.items()),
        f"  roles: dimensions equal {result['roles']['dimensions_equal']}, "
        f"measures equal {result['roles']['measures_equal']}; identifiers equal "
        f"{result['identifiers_equal']}",
    ]
    if result["mismatches"]:
        lines.append("  mismatches:")
        lines.extend(f"    - {item}" for item in result["mismatches"])
    else:
        lines.append("  mismatches: none")
    return lines
