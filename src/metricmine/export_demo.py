"""The demo exporter: the working warehouse's gold schema, as one file.

Spec: docs/spec/serving.md §8 (D-33, over D-03, both as amended by
Record 006). `make export-demo` builds
`demo/demo.duckdb` fresh from the built warehouse: attach the source
READ_ONLY, copy every gold base table in sorted-name order, recreate each
gold view from the catalog's stored SQL re-anchored to the export's own
catalog, then verify. The claim is content equality proven by query, never
byte equality: a DuckDB file embeds storage details that make byte
determinism a claim this project does not need and will not make.

The source is only ever ATTACHed READ_ONLY; the one write surface is the
destination file this module creates. Printing is fine here: this is a
build tool, not the server; the stdio discipline of CLAUDE.md rule 18
governs `src/metricmine/server/`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import duckdb

ENV_VAR = "MM_WAREHOUSE_PATH"
# Both defaults anchor from this module's own location, never the process
# CWD, the same resolution posture as metricmine.query (spec §5).
_REPO = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = _REPO / "warehouse" / "metricmine.duckdb"
DEFAULT_DEST = _REPO / "demo" / "demo.duckdb"

GOLD_SCHEMA = "gold"
# The typed view's ordering key for the content digest: total order over
# the sample, so the digest is deterministic (spec §8, probed August 13).
ORDER_COLUMN = "line_identity"


def _ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def resolve_source_path() -> Path:
    """MM_WAREHOUSE_PATH if set, else the repo-anchored working warehouse."""
    env = os.environ.get(ENV_VAR)
    if env:
        return Path(env)
    return DEFAULT_SOURCE


def _gold_tables(con: duckdb.DuckDBPyConnection, catalog: str) -> list[str]:
    rows = con.execute(
        "select table_name from information_schema.tables"
        " where table_catalog = ? and table_schema = ?"
        " and table_type = 'BASE TABLE' order by table_name",
        [catalog, GOLD_SCHEMA],
    ).fetchall()
    return [row[0] for row in rows]


def _gold_views(con: duckdb.DuckDBPyConnection, catalog: str) -> list[tuple[str, str]]:
    rows = con.execute(
        "select view_name, sql from duckdb_views()"
        " where database_name = ? and schema_name = ? and not internal"
        " order by view_name",
        [catalog, GOLD_SCHEMA],
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


def _view_columns(con: duckdb.DuckDBPyConnection, catalog: str, view: str) -> list[str]:
    rows = con.execute(
        "select column_name from information_schema.columns"
        " where table_catalog = ? and table_schema = ? and table_name = ?"
        " order by ordinal_position",
        [catalog, GOLD_SCHEMA, view],
    ).fetchall()
    return [row[0] for row in rows]


def export(source: Path, dest: Path) -> None:
    """Build dest fresh: gold tables copied, gold views re-anchored (D-33)."""
    if not source.is_file():
        raise FileNotFoundError(
            f"no working warehouse at {source} "
            f"({ENV_VAR}={os.environ.get(ENV_VAR) or 'unset'}). Build it "
            f"first: `make ingest`, then "
            f"`uv run dbt build --project-dir transform --target local`."
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Fresh artifact, never an append: remove the file and its WAL.
    dest.unlink(missing_ok=True)
    Path(str(dest) + ".wal").unlink(missing_ok=True)

    con = duckdb.connect(str(dest))
    try:
        con.execute(f"ATTACH '{source}' AS wh (READ_ONLY)")
        # While wh is attached, schema `gold` exists in two catalogs, so
        # dest-side copy statements carry the dest catalog name to stay
        # independent of binder preference.
        (dest_catalog,) = con.execute("select current_database()").fetchone()
        dest_gold = f"{_ident(dest_catalog)}.{_ident(GOLD_SCHEMA)}"
        con.execute(f"CREATE SCHEMA {dest_gold}")
        for table in _gold_tables(con, "wh"):
            con.execute(
                f"CREATE TABLE {dest_gold}.{_ident(table)}"
                f" AS SELECT * FROM wh.{_ident(GOLD_SCHEMA)}.{_ident(table)}"
            )
        views = _gold_views(con, "wh")
        con.execute("DETACH wh")
        for _view, sql in views:
            # The stored SQL is db-qualified with the source catalog's own
            # name and fails verbatim in another catalog (probed August
            # 13); re-anchor it so the view resolves inside its own file.
            # Created after DETACH: with one catalog attached and its stem
            # deliberately not `gold` (F-25), the plain `gold.` target and
            # body refs bind cleanly.
            con.execute(sql.replace(f"{source.stem}.{GOLD_SCHEMA}.", f"{GOLD_SCHEMA}."))
        con.execute("CHECKPOINT")
    finally:
        con.close()


def _view_digest(path: Path, view: str) -> tuple[int, str]:
    """Row count and ordered content digest, on the file's OWN connection.

    A view's stored refs resolve against its own catalog; comparing views
    through cross-attachment is where the `gold.` qualifier could bind
    ambiguously (probed August 13), so this never attaches anything.
    """
    con = duckdb.connect(str(path), read_only=True)
    try:
        # Deterministic rendering across connections (the D-11 setting).
        con.execute("SET timezone = 'UTC'")
        columns = _view_columns(con, path.stem, view)
        rendered = ", ".join(
            f"coalesce(cast({_ident(c)} as varchar), '')" for c in columns
        )
        line = f"concat_ws(chr(31), {rendered})"
        rel = f"{_ident(GOLD_SCHEMA)}.{_ident(view)}"
        count, digest = con.execute(
            f"select count(*),"
            f" md5(string_agg({line}, chr(10) order by {_ident(ORDER_COLUMN)}))"
            f" from {rel}"
        ).fetchone()
        return int(count), digest
    finally:
        con.close()


def verify(source: Path, dest: Path) -> dict[str, Any]:
    """The D-33 claim: content equality by query. Raises on any inequality.

    Tables compare through ONE comparator connection with both files
    attached read-only: equal counts plus symmetric EXCEPT both ways
    returning zero. Views compare by ordered content digest across direct
    per-file connections, never cross-attachment.
    """
    report: dict[str, Any] = {"tables": [], "views": []}
    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{source}' AS src (READ_ONLY)")
        con.execute(f"ATTACH '{dest}' AS exp (READ_ONLY)")
        src_tables = _gold_tables(con, "src")
        exp_tables = _gold_tables(con, "exp")
        if src_tables != exp_tables:
            raise RuntimeError(
                f"gold table sets differ: source {src_tables}, export {exp_tables}"
            )
        for table in src_tables:
            rel = f"{_ident(GOLD_SCHEMA)}.{_ident(table)}"
            (src_count,) = con.execute(f"select count(*) from src.{rel}").fetchone()
            (exp_count,) = con.execute(f"select count(*) from exp.{rel}").fetchone()
            if src_count != exp_count:
                raise RuntimeError(
                    f"{table}: row counts differ (source {src_count}, "
                    f"export {exp_count})"
                )
            for a, b in (("src", "exp"), ("exp", "src")):
                (extra,) = con.execute(
                    f"select count(*) from"
                    f" (select * from {a}.{rel} except select * from {b}.{rel})"
                ).fetchone()
                if extra:
                    raise RuntimeError(
                        f"{table}: {extra} row(s) in {a} and not in {b}"
                    )
            report["tables"].append({"table": table, "rows": int(src_count)})
        src_views = [name for name, _sql in _gold_views(con, "src")]
        exp_views = [name for name, _sql in _gold_views(con, "exp")]
        if src_views != exp_views:
            raise RuntimeError(
                f"gold view sets differ: source {src_views}, export {exp_views}"
            )
    finally:
        con.close()
    for view in src_views:
        src_count, src_digest = _view_digest(source, view)
        exp_count, exp_digest = _view_digest(dest, view)
        if (src_count, src_digest) != (exp_count, exp_digest):
            raise RuntimeError(
                f"{view}: content digests differ "
                f"(source {src_count} rows {src_digest}, "
                f"export {exp_count} rows {exp_digest})"
            )
        report["views"].append(
            {"view": view, "rows": src_count, "digest": src_digest, "match": True}
        )
    return report


def main() -> None:
    source = resolve_source_path()
    dest = DEFAULT_DEST
    export(source, dest)
    report = verify(source, dest)
    print(f"exported {source} -> {dest}")
    print(f"tables: {len(report['tables'])}")
    for entry in report["tables"]:
        print(f"  {entry['table']}: {entry['rows']} rows")
    for entry in report["views"]:
        print(
            f"view {entry['view']}: {entry['rows']} rows, "
            f"digest match ({entry['digest']})"
        )
    print(f"artifact size: {dest.stat().st_size} bytes")


if __name__ == "__main__":
    main()
