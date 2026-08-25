"""The deterministic enforcement helper for adopted silver models (D-16
Amendment J, F-27).

At adoption, `datacontract dbt sync` CREATES the silver properties file
from the approved contract with exact DuckDB data types, but writes
neither `config.contract.enforced` nor column `constraints` (measured,
adoption lab, August 21, 2026; F-27). This helper writes ONLY those two
keys, and only what the contract already declares: `contract.enforced:
true` and a `not_null` constraint per contract-required column. It
writes nothing else and touches no other file; the properties file
stays human-owned and the edit is reviewed in the model PR diff (rule
11). Idempotent: a second run changes nothing. NOT an agent (D-10
Amendment G, CLAUDE.md rule 15): no model call, no network, no loop.
This is a CLI, not the stdio server: stdout carries results and stderr
diagnostics (rule 18's stdout discipline governs the server only).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml


def run(repo_root: Path, table: str) -> int:
    """0: enforced (edited, or already). 1: a precondition unmet."""
    contract_path = repo_root / "contracts" / f"{table}.odcs.yaml"
    if not contract_path.is_file():
        print(
            f"error: no approved contract at {contract_path}; "
            f"enforce-properties runs after the contract PR merges "
            f"(D-35 adoption order: describe, review, contract PR, sync, "
            f"enforce-properties, model PR)",
            file=sys.stderr,
        )
        return 1
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    properties_path = (
        repo_root / "transform" / "models" / "silver" / f"{table}.yml"
    )
    if not properties_path.is_file():
        print(
            f"error: no properties file at {properties_path}; run "
            f"`uv run datacontract dbt sync {contract_path} --project-dir "
            f"transform --target local` first, which creates it from the "
            f"approved contract with exact types (F-27)",
            file=sys.stderr,
        )
        return 1
    document = yaml.safe_load(properties_path.read_text(encoding="utf-8"))
    model = next(
        (
            entry
            for entry in (document or {}).get("models") or []
            if entry.get("name") == table
        ),
        None,
    )
    if model is None:
        print(
            f"error: {properties_path} carries no model entry named "
            f"{table!r}",
            file=sys.stderr,
        )
        return 1
    required = [
        prop["name"]
        for prop in contract["schema"][0]["properties"]
        if prop.get("required")
    ]
    columns = {
        entry.get("name"): entry for entry in model.get("columns") or []
    }
    missing = sorted(set(required) - set(columns))
    if missing:
        print(
            f"error: contract-required column(s) absent from "
            f"{properties_path}: {', '.join(missing)}; re-run sync so the "
            f"file carries every contracted column (F-27)",
            file=sys.stderr,
        )
        return 1

    edits: list[str] = []
    config = model.setdefault("config", {})
    contract_block = config.setdefault("contract", {})
    if contract_block.get("enforced") is not True:
        contract_block["enforced"] = True
        edits.append("config.contract.enforced: true")
    for name in required:
        constraints = columns[name].setdefault("constraints", [])
        if not any(entry.get("type") == "not_null" for entry in constraints):
            constraints.append({"type": "not_null"})
            edits.append(f"columns.{name}.constraints: not_null")

    if not edits:
        print(f"{properties_path} is already enforced; no changes (idempotent)")
        return 0
    tmp = properties_path.with_suffix(properties_path.suffix + ".tmp")
    tmp.write_text(
        yaml.safe_dump(
            document,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=88,
        ),
        encoding="utf-8",
    )
    os.replace(tmp, properties_path)
    print(f"enforced {properties_path}:")
    for edit in edits:
        print(f"  + {edit}")
    print(
        "review the diff in the model PR (rule 11); delete any "
        "accepted_values [0] test on sight (F-05)"
    )
    return 0
