"""Prep probe: SQL-vs-Python parity for canonical_key v2 golden vectors.

Recomputes every payload vector's canonical serialization and key through
DuckDB SQL at the pinned engine — lower(to_json(struct_pack(...))) over
VARCHAR-cast members in lowercase-sorted field order, then sha256() —
and every manifest vector through lower(to_json(<VARCHAR list>)) +
sha256(). Fails loudly on any byte disagreement with the golden file.

This is the function-level half of the dual-implementation proof, run at
prep so Sitting H commits pre-verified vectors; the dbt-path half (the
committed consistency test over emitted models) lands with the engine at
Sitting I per the ladder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

GOLDEN = (Path(__file__).resolve().parents[1] / "metricmine" / "tests"
          / "golden" / "canonical_key_v2.json")


def sql_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def member_expr(typed: dict) -> str:
    t = typed["t"]
    if t == "null":
        return "CAST(NULL AS VARCHAR)"
    v = typed.get("v")
    if t == "str":
        return f"CAST({sql_str(v)} AS VARCHAR)"
    if t == "int":
        return f"CAST(CAST({v} AS INTEGER) AS VARCHAR)"
    if t == "decimal":
        return f"CAST(CAST({sql_str(v)} AS DECIMAL(10,2)) AS VARCHAR)"
    if t == "timestamp":
        return f"CAST(TIMESTAMP {sql_str(v)} AS VARCHAR)"
    if t == "date":
        return f"CAST(DATE {sql_str(v)} AS VARCHAR)"
    if t == "bool":
        return f"CAST({'true' if v else 'false'} AS VARCHAR)"
    raise ValueError(t)


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def payload_sql(fields: dict) -> str:
    ordered = sorted(fields.items(), key=lambda kv: kv[0].lower())
    members = ", ".join(
        f"{quote_ident(name)} := {member_expr(typed)}" for name, typed in ordered
    )
    return f"SELECT lower(to_json(struct_pack({members})))::VARCHAR AS canon"


def manifest_sql(names: list[str]) -> str:
    items = ", ".join(sql_str(n) for n in names)
    return f"SELECT lower(to_json([{items}]))::VARCHAR AS canon"


def main() -> int:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    con = duckdb.connect()
    print(f"duckdb {duckdb.__version__}")
    failures = 0

    for vec in golden["payload"]:
        for field_set_name in ("fields", "fields_alt"):
            if field_set_name not in vec:
                continue
            q = payload_sql(vec[field_set_name])
            canon = con.execute(q).fetchone()[0]
            key = con.execute(
                f"WITH c AS ({q}) SELECT sha256(canon) FROM c"
            ).fetchone()[0]
            ok = canon == vec["canonical"] and key == vec["key"]
            status = "OK " if ok else "FAIL"
            if not ok:
                failures += 1
                print(f"{status} payload/{vec['name']}/{field_set_name}")
                print(f"  sql canon: {canon!r}")
                print(f"  py  canon: {vec['canonical']!r}")
                print(f"  sql key:   {key}")
                print(f"  py  key:   {vec['key']}")
            else:
                print(f"{status} payload/{vec['name']}/{field_set_name}: {key}")

    for vec in golden["manifest"]:
        for name_set in ("names", "names_alt"):
            if name_set not in vec:
                continue
            q = manifest_sql(vec[name_set])
            canon = con.execute(q).fetchone()[0]
            key = con.execute(
                f"WITH c AS ({q}) SELECT sha256(canon) FROM c"
            ).fetchone()[0]
            ok = canon == vec["canonical"] and key == vec["key"]
            status = "OK " if ok else "FAIL"
            if not ok:
                failures += 1
                print(f"{status} manifest/{vec['name']}/{name_set}")
                print(f"  sql canon: {canon!r}\n  py  canon: {vec['canonical']!r}")
                print(f"  sql key: {key}\n  py  key: {vec['key']}")
            else:
                print(f"{status} manifest/{vec['name']}/{name_set}: {key}")

    total_payload = sum(1 + ("fields_alt" in v) for v in golden["payload"])
    total_manifest = sum(1 + ("names_alt" in v) for v in golden["manifest"])
    print(f"\n{total_payload} payload + {total_manifest} manifest"
          f" serializations checked; failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
