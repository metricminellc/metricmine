"""The adoption scan: a deterministic inventory of the dbt model tree
(D-35).

THIS IS NOT AN AGENT (D-10 Amendment G, CLAUDE.md rule 15): pure Python
over the standard library plus duckdb and pyyaml, no model call, no
network, no loop. The two proposers stay the only LLM surface; this
module is the deterministic code that decides WHICH stance to run next,
and on which table. It writes no contract, edits nothing under
transform/, and never writes the warehouse, which opens read-only
through the project's own protocol (D-11) and entirely through its
public methods (relation_kinds landed for exactly this).

The review queue is DERIVED, never stored (D-35): no scan database, no
status column, no state file that could go stale. Every run re-reads the
model tree, contracts/, profiles/, config/default.yaml, and the live
warehouse, and recomputes each state from scratch; do a step, re-run,
and the queue flips. Output lands under the gitignored proposals/
outbox (D-24) as plan.md plus plan.json; the plan body carries a
content hash and no timestamp, so the same state always hashes the
same.

Jurisdiction, by decision: engine-emitted gold under the ownership
manifest is skipped (D-09, rule 8; regeneration is a PR, never an
adoption). A gold model OUTSIDE the manifest is `skip_foreign_gold`:
gold stays engine-owned, a typed surface the engine does not emit is
never proposed (rule 12 as amended by D-36), and foreign gold marts are
reported, never adopted (D-35); migrating one is a register decision.

This is a CLI, not the stdio server: stdout carries the plan and stderr
diagnostics (rule 18's stdout discipline governs the server only).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from metricmine.warehouse.duckdb import DuckDBWarehouse

LAYER_ORDER = {"bronze": 0, "silver": 1, "gold": 2}
QUEUE_ORDER = [
    "adopt",
    "amend",
    "unenforced",
    "needs_profile",
    "needs_build",
    "contract_ahead",
]
SKIP_STATES = [
    "skip_engine_owned",
    "skip_foreign_gold",
    "skip_view",
    "skip_unknown_layer",
]
ALL_STATES = QUEUE_ORDER + SKIP_STATES + ["in_sync"]
# dbt honours an in-file config() block above the properties file, and
# both above the dbt_project.yml folder default; resolve in that order.
_SQL_MATERIALIZED = re.compile(
    r"config\s*\([^)]*materialized\s*=\s*['\"](\w+)['\"]"
)


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _head_sha(repo: Path) -> str:
    """The repo head, the only per-clone line in the plan body."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() or "unknown"


def _dbt_defaults(repo: Path) -> dict:
    """Folder-level +materialized and +schema from dbt_project.yml."""
    cfg = _load_yaml(repo / "transform" / "dbt_project.yml")
    project = (cfg.get("models") or {}).get(cfg.get("name", "metricmine"), {})
    defaults: dict[str, dict] = {}
    for layer, block in (project or {}).items():
        if isinstance(block, dict):
            defaults[layer] = {
                "materialized": block.get("+materialized", "view"),
                "schema": block.get("+schema", layer),
            }
    return defaults


def _ownership(repo: Path) -> set[str]:
    path = repo / "transform" / "models" / "gold" / "ownership-manifest.json"
    if not path.is_file():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")).get("files", {}))


def _read_contracts(repo: Path) -> tuple[dict, list]:
    """Table contracts indexed by schema-object name; mapping contracts
    listed as engine inputs, never models (rule 9).

    One contract file may carry MANY table objects: the gold star
    contract covers every star table as one versioned unit, so coverage
    is indexed over every table-typed schema object in every contract,
    never schema[0] alone (adoption lab, August 21, 2026).
    """
    tables: dict[str, dict] = {}
    mappings: list[dict] = []
    contracts_dir = repo / "contracts"
    if not contracts_dir.is_dir():
        return tables, mappings
    for path in sorted(contracts_dir.glob("*.odcs.yaml")):
        doc = _load_yaml(path)
        for obj in doc.get("schema") or []:
            entry = {
                "file": path.name,
                "id": doc.get("id"),
                "version": doc.get("version"),
                "object": obj.get("name"),
                "properties": obj.get("properties") or [],
            }
            if obj.get("physicalType") == "mapping":
                entry["source_table"] = obj.get("sourceTable")
                mappings.append(entry)
            elif obj.get("physicalType") == "table":
                tables[obj.get("name")] = entry
    return tables, mappings


def _read_properties(folder: Path) -> dict:
    """models[].name to its properties entry, across the folder's ymls."""
    out: dict[str, dict] = {}
    for path in sorted(folder.glob("*.yml")) + sorted(folder.glob("*.yaml")):
        doc = _load_yaml(path)
        for model in doc.get("models") or []:
            if model.get("name"):
                out[model["name"]] = {"file": path.name, "entry": model}
    return out


def _read_profile(repo: Path, schema: str, table: str) -> dict | None:
    """The newest vNNNN.json under profiles/<schema>.<table>/, sidecars
    (.meta.json) skipped."""
    folder = repo / "profiles" / f"{schema}.{table}"
    if not folder.is_dir():
        return None
    versions = [
        path
        for path in sorted(folder.glob("v[0-9]*.json"))
        if not path.name.endswith(".meta.json")
    ]
    if not versions:
        return None
    doc = json.loads(versions[-1].read_text(encoding="utf-8"))
    return {
        "version": versions[-1].stem,
        "content_hash": doc.get("content_hash"),
        "columns": (doc.get("dataset") or {}).get("columns", []),
    }


def _profiling_config(repo: Path) -> dict:
    return _load_yaml(repo / "config" / "default.yaml").get("profiling") or {}


def _profiling_targets(repo: Path) -> set[tuple[str, str]]:
    return {
        (target["schema"], target["table"])
        for target in _profiling_config(repo).get("targets") or []
    }


def _warehouse_path(repo: Path) -> Path:
    return repo / _profiling_config(repo).get(
        "warehouse_path", "warehouse/metricmine.duckdb"
    )


def _relative_warehouse(repo: Path) -> str:
    """The warehouse path repo-relative in the plan body, so two
    machines at the same state produce the same body (the head SHA is
    the only per-clone line)."""
    path = _warehouse_path(repo)
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:  # a configured absolute path outside the repo
        return path.as_posix()


def _warehouse_snapshot(repo: Path, schemas: list[str]) -> dict:
    """Read-only, entirely through the protocol (D-11): relation_kinds
    tells views from tables, so nothing reaches past the public
    methods. Views report no row count: counting one queries the
    underlying star, and a projection's row count is a property of its
    inputs, not of the model file. A missing warehouse file yields an
    empty snapshot, and every model then reads needs_build."""
    path = _warehouse_path(repo)
    snapshot: dict[tuple[str, str], dict] = {}
    if not path.is_file():
        return snapshot
    with DuckDBWarehouse(path) as warehouse:
        for schema in schemas:
            for table, kind in warehouse.relation_kinds(schema).items():
                snapshot[(schema, table)] = {
                    "relation_type": kind,
                    "columns": warehouse.columns(schema, table),
                    "row_count": (
                        warehouse.row_count(schema, table)
                        if kind == "table"
                        else None
                    ),
                }
    return snapshot


def _agreement(contract_props: list, profile_cols: list) -> dict:
    """First-class agreement, the stance-probe scope exactly: per
    contract column, presence in the profile, physicalType equality,
    required == (null_rate == 0.0); plus profile columns absent from
    the contract."""
    profiled = {column["name"]: column for column in profile_cols}
    checked = agree = 0
    mismatches: list[str] = []
    for prop in contract_props:
        name = prop["name"]
        column = profiled.get(name)
        if column is None:
            mismatches.append(f"{name}: in contract, absent from profile")
            continue
        for field, want, got in (
            (
                "physicalType",
                prop.get("physicalType"),
                column.get("physical_type"),
            ),
            (
                "required",
                bool(prop.get("required", False)),
                column.get("null_rate") == 0.0,
            ),
        ):
            checked += 1
            if want == got:
                agree += 1
            else:
                mismatches.append(
                    f"{name}.{field}: contract={want!r} profile={got!r}"
                )
    contract_names = {prop["name"] for prop in contract_props}
    for name in profiled:
        if name not in contract_names:
            mismatches.append(f"{name}: in profile, absent from contract")
    return {"checks": checked, "agree": agree, "mismatches": mismatches}


def _relation_vs_contract(contract_props: list, rel_columns: list) -> dict:
    """The contract against the LIVE relation, names and physical types
    both ways, so drift is visible before a fresh profile exists."""
    live = dict(rel_columns)
    contract_ahead: list[str] = []
    type_drift: list[str] = []
    relation_ahead: list[str] = []
    for prop in contract_props:
        name = prop["name"]
        if name not in live:
            contract_ahead.append(name)
        elif prop.get("physicalType") != live[name]:
            type_drift.append(
                f"{name}: contract={prop.get('physicalType')!r} "
                f"relation={live[name]!r}"
            )
    contract_names = {prop["name"] for prop in contract_props}
    for name in live:
        if name not in contract_names:
            relation_ahead.append(name)
    return {
        "contract_ahead": contract_ahead,
        "type_drift": type_drift,
        "relation_ahead": relation_ahead,
    }


def _enforcement(props_entry: dict | None) -> dict:
    if not props_entry:
        return {"exists": False, "enforced": False, "contract_id": None}
    cfg = props_entry["entry"].get("config") or {}
    return {
        "exists": True,
        "enforced": bool((cfg.get("contract") or {}).get("enforced")),
        "contract_id": (
            (cfg.get("meta") or {}).get("datacontract_cli") or {}
        ).get("contract_id"),
    }


def _classify(model: dict) -> tuple[str, str, str]:
    """One state per model, in this precedence: the jurisdiction skips,
    the layer and view skips, build, profile, then the contract states.
    `contract_ahead` outranks `amend` so the operator is never told to
    weaken a contract to match a lagging relation (rule 6). Returns
    (state, next_command, reason)."""
    name = model["name"]
    rvc = model["relation_vs_contract"]
    if model["layer"] == "gold" and model["engine_owned"]:
        also = (
            " Also a view (D-17 typed projection, uncontracted by design)."
            if model["materialization"] == "view"
            else ""
        )
        return (
            "skip_engine_owned",
            "none",
            "engine-emitted under the ownership manifest (D-09, rule 8);"
            f" regeneration is a PR, never an adoption.{also}",
        )
    if model["layer"] == "gold":
        return (
            "skip_foreign_gold",
            "none (reported, never adopted)",
            "a gold model outside the ownership manifest: gold stays"
            " engine-owned (D-09), a typed surface the engine does not"
            " emit is never proposed (rule 12), and foreign gold marts"
            " are reported, never adopted (D-35); migrating one is a"
            " register decision.",
        )
    if model["layer"] not in LAYER_ORDER:
        return (
            "skip_unknown_layer",
            "none",
            f"model folder {model['layer']!r} is not a medallion layer;"
            " the scan classifies bronze, silver, and gold only.",
        )
    if model["materialization"] == "view":
        return (
            "skip_view",
            "re-materialize as table before adoption (rule 7)",
            "contract enforcement requires table or incremental (rule 7);"
            " views are uncontracted.",
        )
    if not model["relation"]:
        return (
            "needs_build",
            "uv run dbt build --project-dir transform --profiles-dir"
            f" transform --target local --select {name}",
            f"no relation {model['schema']}.{name} in the warehouse.",
        )
    if not model["profile"]:
        return (
            "needs_profile",
            f"add {{schema: {model['schema']}, table: {name}}} to"
            " config/default.yaml profiling.targets, then: make profile",
            "the describe stance reads exactly one profile artifact"
            " (rule 15); there is none.",
        )
    if not model["contract"]:
        return (
            "adopt",
            f"make propose-describe TABLE={name}  &&  make verify-grain"
            f" TABLE={name} KEYS=...",
            "relation and profile present, no contract governs it.",
        )
    cid = f"{model['contract']['id']}@{model['contract']['version']}"
    if rvc["contract_ahead"]:
        return (
            "contract_ahead",
            f"model change pending for contract {cid}",
            "contract declares columns the relation lacks: "
            + ", ".join(rvc["contract_ahead"])
            + ".",
        )
    drift = (
        (model["agreement"]["mismatches"] if model["agreement"] else [])
        + rvc["type_drift"]
        + [
            f"{column}: in relation, absent from contract"
            for column in rvc["relation_ahead"]
        ]
    )
    if drift:
        return (
            "amend",
            f'make propose-amend TABLE={name} INTENT="..."',
            f"{len(drift)} disagreement(s) against {cid}: {drift[0]}",
        )
    if not (
        model["enforcement"]["enforced"] and model["enforcement"]["contract_id"]
    ):
        return (
            "unenforced",
            "author the properties file (rule 11): sync creates it,"
            " make enforce-properties adds the two keys",
            f"{cid} agrees with the relation, but the dbt properties"
            " file declares no config.contract.enforced plus"
            " config.meta.datacontract_cli.contract_id.",
        )
    return (
        "in_sync",
        "none",
        f"{cid} enforced and in agreement with the relation and profile.",
    )


def inventory(repo: Path) -> dict:
    """Every model file classified, from the tree and the read-only
    warehouse, on this call; nothing cached, nothing stored."""
    defaults = _dbt_defaults(repo)
    owned = _ownership(repo)
    table_contracts, mapping_contracts = _read_contracts(repo)
    targets = _profiling_targets(repo)
    schemas = sorted(
        {entry["schema"] for entry in defaults.values()} | {"bronze"}
    )
    snapshot = _warehouse_snapshot(repo, schemas)
    properties_cache: dict[Path, dict] = {}
    models = []
    for sql in sorted((repo / "transform" / "models").rglob("*.sql")):
        rel_path = sql.relative_to(repo).as_posix()
        layer = sql.parent.name
        name = sql.stem
        default = defaults.get(layer, {"materialized": "view", "schema": layer})
        schema = default["schema"]
        if sql.parent not in properties_cache:
            properties_cache[sql.parent] = _read_properties(sql.parent)
        props = properties_cache[sql.parent].get(name)
        in_sql = _SQL_MATERIALIZED.search(sql.read_text(encoding="utf-8"))
        declared = in_sql.group(1) if in_sql else None
        if declared is None and props:
            declared = (props["entry"].get("config") or {}).get("materialized")
        declared = declared or default["materialized"]
        relation = snapshot.get((schema, name))
        materialization = (
            "view"
            if (
                declared == "view"
                or (relation and relation["relation_type"] == "view")
            )
            else declared
        )
        contract = table_contracts.get(name)
        profile = _read_profile(repo, schema, name)
        model = {
            "name": name,
            "layer": layer,
            "path": rel_path,
            "schema": schema,
            "materialization": materialization,
            "declared_materialization": declared,
            "engine_owned": rel_path in owned,
            "properties_file": props["file"] if props else None,
            "enforcement": _enforcement(props),
            "relation": relation
            and {
                "type": relation["relation_type"],
                "columns": len(relation["columns"]),
                "row_count": relation["row_count"],
            },
            "contract": contract
            and {
                key: contract[key]
                for key in ("file", "id", "version", "object")
            },
            "profile": profile
            and {
                "version": profile["version"],
                "content_hash": profile["content_hash"],
            },
            "profiling_target": (schema, name) in targets,
        }
        model["agreement"] = (
            _agreement(contract["properties"], profile["columns"])
            if (contract and profile)
            else None
        )
        model["relation_vs_contract"] = (
            _relation_vs_contract(contract["properties"], relation["columns"])
            if (contract and relation)
            else {"contract_ahead": [], "type_drift": [], "relation_ahead": []}
        )
        model["state"], model["next_command"], model["reason"] = _classify(
            model
        )
        models.append(model)
    models.sort(key=lambda m: (LAYER_ORDER.get(m["layer"], 9), m["name"]))
    return {
        "models": models,
        "mapping_contracts": mapping_contracts,
        "warehouse_relations": len(snapshot),
    }


def _counts(models: list[dict]) -> dict[str, int]:
    """Nonzero state counts in the fixed ALL_STATES order."""
    counts = {
        state: sum(1 for model in models if model["state"] == state)
        for state in ALL_STATES
    }
    return {state: count for state, count in counts.items() if count}


def _row(model: dict) -> str:
    relation = model["relation"]
    contract = model["contract"]
    profile = model["profile"]
    agreement = model["agreement"]
    rel = (
        "missing"
        if not relation
        else (
            f"{relation['type']}, {relation['columns']} cols"
            + (
                f", {relation['row_count']} rows"
                if relation["row_count"] is not None
                else ""
            )
        )
    )
    con = f"{contract['id']}@{contract['version']}" if contract else "none"
    prof = (
        f"{profile['version']}"
        f"{'' if model['profiling_target'] else ' (untargeted)'}"
        if profile
        else "none"
    )
    agr = (
        (
            f"{agreement['agree']}/{agreement['checks']}, "
            + (
                f"{len(agreement['mismatches'])} mismatch"
                if agreement["mismatches"]
                else "clean"
            )
        )
        if agreement
        else "n/a"
    )
    rvc = model["relation_vs_contract"]
    if any(rvc.values()):
        agr += (
            f"; rel_vs_contract {len(rvc['contract_ahead'])} ahead /"
            f" {len(rvc['type_drift'])} type /"
            f" {len(rvc['relation_ahead'])} extra"
        )
    return (
        f"| `{model['name']}` | {model['layer']} |"
        f" {model['materialization']} | {rel} | {con} | {prof} | {agr} |"
        f" `{model['state']}` |"
    )


def render_md(repo: Path, inv: dict, head: str) -> str:
    """The plan body: no timestamp, so the same state hashes the same."""
    models = inv["models"]
    counts = _counts(models)
    lines = [
        "# MetricMine adoption scan: the plan",
        "",
        "Deterministic scan, not an agent (D-35). The queue below is"
        " DERIVED from the model tree, contracts/, profiles/,"
        " config/default.yaml, and the live warehouse on this run;"
        " nothing is stored. Re-run after each step and the states flip.",
        "",
        f"- repo head: `{head}`",
        f"- warehouse: `{_relative_warehouse(repo)}`"
        f" (opened read-only, D-11), {inv['warehouse_relations']} relations",
        f"- models scanned: {len(models)}",
        "",
        "| state | models |",
        "| --- | --- |",
    ]
    lines += [f"| `{state}` | {count} |" for state, count in counts.items()]
    lines += [
        "",
        "## Inventory",
        "",
        "| model | layer | mat | relation | contract | profile |"
        " agreement | state |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines += [_row(model) for model in models]
    lines += ["", "## The queue", ""]
    queued = sorted(
        (model for model in models if model["state"] in QUEUE_ORDER),
        key=lambda model: (
            QUEUE_ORDER.index(model["state"]),
            LAYER_ORDER.get(model["layer"], 9),
            model["name"],
        ),
    )
    if not queued:
        lines += ["Empty. Every model is in sync or skipped by decision.", ""]
    for position, model in enumerate(queued, 1):
        lines += [
            f"{position}. **`{model['name']}`**: `{model['state']}`  ",
            f"   why: {model['reason']}  ",
            f"   next: `{model['next_command']}`",
            "",
        ]
    lines += ["## Skipped, by decision", ""]
    skipped = [
        f"- `{model['name']}`: `{model['state']}`: {model['reason']}"
        for model in models
        if model["state"] in SKIP_STATES
    ]
    lines += skipped or ["- none"]
    lines += ["", "## In sync, no action", ""]
    in_sync = [
        f"- `{model['name']}`: {model['reason']}"
        for model in models
        if model["state"] == "in_sync"
    ]
    lines += in_sync or ["- none"]
    lines += ["", "## Engine inputs, not models", ""]
    mappings = [
        f"- `{entry['file']}`: {entry['id']}@{entry['version']}, object"
        f" `{entry['object']}` (physicalType: mapping) over"
        f" `{entry.get('source_table')}`. Rule 9: engine input; no"
        f" physical table ever carries this name."
        for entry in inv["mapping_contracts"]
    ]
    lines += mappings or ["- none"]
    lines.append("")
    return "\n".join(lines)


def run(repo: Path, now: datetime | None = None) -> int:
    """Derive the queue, write plan.md and plan.json to the outbox,
    print the plan. Always 0: the scan reports, it never judges."""
    head = _head_sha(repo)
    inv = inventory(repo)
    body = render_md(repo, inv, head)
    plan_hash = _sha256_text(body)
    now = now or datetime.now(timezone.utc)
    stamp = f"{now.strftime('%Y%m%dT%H%M%S')}{now.microsecond:06d}Z"
    out_dir = repo / "proposals" / "scan" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    md = (
        body
        + "\n---\nplan_hash (over the body above, this line excluded): "
        + f"`{plan_hash}`\n"
    )
    (out_dir / "plan.md").write_text(md, encoding="utf-8")
    plan = {
        "scan_schema_version": "1.0.0",
        # generated_at is excluded from plan_hash by construction: the
        # hash covers the plan body, which carries no time.
        "generated_at": now.isoformat(),
        "head_sha": head,
        "warehouse_path": _relative_warehouse(repo),
        "plan_hash": plan_hash,
        "counts": _counts(inv["models"]),
        "models": inv["models"],
        "mapping_contracts": inv["mapping_contracts"],
    }
    (out_dir / "plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(md, end="")
    print(
        f"\nwrote {(out_dir / 'plan.md').relative_to(repo)}"
        f" and {(out_dir / 'plan.json').relative_to(repo)}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    repo = Path(args[0]).resolve() if args else Path.cwd()
    return run(repo)
