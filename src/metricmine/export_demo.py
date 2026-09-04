"""The demo exporter: the working warehouse's gold schema, as one file.

Spec: docs/spec/serving.md §8 (D-33, over D-03, both as amended by
Record 006). `make export-demo` builds
`demo/demo.duckdb` fresh from the built warehouse: attach the source
READ_ONLY, copy every gold base table in sorted-name order, recreate each
gold view from the catalog's stored SQL re-anchored to the export's own
catalog, then verify. The claim is content equality proven by query, never
byte equality: a DuckDB file embeds storage details that make byte
determinism a claim this project does not need and will not make.

The source is only ever ATTACHed READ_ONLY; the two write surfaces are
the destination file this module creates and, since D-03 Amendment S
(Arc 6), the digest manifest beside it: `demo/demo.digest.json`, the
committed statement of what the published artifact contains (every gold
table's row count, every gold view's row count and ordered content
digest, and the registry's row count and ordered digest over its
deterministic columns) and, when MM_DEMO_RELEASE names the release the artifact ships
with, the artifact's own sha256 and size. The artifact itself is a
release asset, never committed; `make demo-fetch` restores it from the
release named in the manifest and verifies it against the manifest; CI
proves a fresh build against the manifest (scripts/check_demo_digest.py).
Printing is fine here: this is a build tool, not the server; the stdio
discipline of CLAUDE.md rule 18 governs `src/metricmine/server/`.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import duckdb

ENV_VAR = "MM_WAREHOUSE_PATH"
RELEASE_ENV_VAR = "MM_DEMO_RELEASE"
MANIFEST_SCHEMA_VERSION = "1.0.0"
# Both defaults anchor from this module's own location, never the process
# CWD, the same resolution posture as metricmine.query (spec §5).
_REPO = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = _REPO / "warehouse" / "metricmine.duckdb"
DEFAULT_DEST = _REPO / "demo" / "demo.duckdb"
DEFAULT_MANIFEST = _REPO / "demo" / "demo.digest.json"

GOLD_SCHEMA = "gold"
REGISTRY_TABLE = "context_registry"
# The registry's deterministic columns (D-30): everything but loaded_at,
# the build stamp F-39 keeps out of every content comparison. The digest
# over these, ordered by schema_key, makes a registry change visible to
# the manifest gate even though row counts stay put.
REGISTRY_COLUMNS = (
    "schema_key",
    "entity_group",
    "contract_name",
    "contract_version",
    "compiled_context",
)
# The content digest orders each view's rendered rows by the rendered row
# text itself: a total order over the content that needs no per-category
# key, so one digest rule covers every typed view the star serves (spec §8
# as amended at the multi-source fan-in, D-41). Before the fan-in the
# order key was the invoice_lines derived identity, a one-category name.


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
            f" md5(string_agg(line, chr(10) order by line))"
            f" from (select {line} as line from {rel})"
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


def _registry_digest(con: duckdb.DuckDBPyConnection) -> tuple[int, str]:
    """Row count and ordered digest over the registry's deterministic
    columns (never loaded_at, F-39), so a registry content change is
    visible to the manifest gate at equal row counts."""
    rendered = ", ".join(
        f"coalesce(cast({_ident(c)} as varchar), '')" for c in REGISTRY_COLUMNS
    )
    line = f"concat_ws(chr(31), {rendered})"
    rel = f"{_ident(GOLD_SCHEMA)}.{_ident(REGISTRY_TABLE)}"
    count, digest = con.execute(
        f"select count(*), md5(string_agg(line, chr(10) order by line))"
        f" from (select {line} as line from {rel})"
    ).fetchone()
    return int(count), digest


def content_manifest(path: Path) -> dict[str, Any]:
    """The content section of the digest manifest, measured on one file:
    every gold table's row count, every gold view's row count and ordered
    content digest, and the registry's row count and ordered digest over
    its deterministic columns (the D-33 claim, in a committed form)."""
    con = duckdb.connect(str(path), read_only=True)
    try:
        con.execute("SET timezone = 'UTC'")
        tables = _gold_tables(con, path.stem)
        views = [name for name, _sql in _gold_views(con, path.stem)]
        counts = {}
        for table in tables:
            rel = f"{_ident(GOLD_SCHEMA)}.{_ident(table)}"
            (count,) = con.execute(f"select count(*) from {rel}").fetchone()
            counts[table] = {"rows": int(count)}
        registry = None
        if REGISTRY_TABLE in tables:
            rows, digest = _registry_digest(con)
            registry = {"rows": rows, "digest": digest}
    finally:
        con.close()
    digests = {}
    for view in views:
        count, digest = _view_digest(path, view)
        digests[view] = {"rows": count, "digest": digest}
    return {"registry": registry, "tables": counts, "views": digests}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(dest: Path, release: str | None) -> dict[str, Any]:
    """The digest manifest for an exported artifact.

    ``release`` names the GitHub release the artifact ships with (the exit
    sitting exports with MM_DEMO_RELEASE set); None means the tree has no
    published artifact yet, and `make demo-fetch` says so.
    """
    return {
        "artifact": {
            "name": dest.name,
            "release": release,
            "sha256": file_sha256(dest),
            "bytes": dest.stat().st_size,
        },
        "content": content_manifest(dest),
        "schema_version": MANIFEST_SCHEMA_VERSION,
    }


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_content(path: Path, manifest: dict[str, Any]) -> list[str]:
    """Differences between a file's gold content and a manifest's content
    section, as human-readable lines; empty means the file serves exactly
    what the manifest states."""
    measured = content_manifest(path)
    expected = manifest["content"]
    problems: list[str] = []
    if set(measured["tables"]) != set(expected["tables"]):
        problems.append(
            f"gold table sets differ: file {sorted(measured['tables'])},"
            f" manifest {sorted(expected['tables'])}"
        )
    if set(measured["views"]) != set(expected["views"]):
        problems.append(
            f"gold view sets differ: file {sorted(measured['views'])},"
            f" manifest {sorted(expected['views'])}"
        )
    for table, entry in expected["tables"].items():
        got = measured["tables"].get(table)
        if got and got["rows"] != entry["rows"]:
            problems.append(
                f"table {table}: {got['rows']} rows, manifest {entry['rows']}"
            )
    for view, entry in expected["views"].items():
        got = measured["views"].get(view)
        if got and (got["rows"], got["digest"]) != (entry["rows"], entry["digest"]):
            problems.append(
                f"view {view}: {got['rows']} rows digest {got['digest']},"
                f" manifest {entry['rows']} rows digest {entry['digest']}"
            )
    if measured.get("registry") != expected.get("registry"):
        problems.append(
            f"registry: file {measured.get('registry')},"
            f" manifest {expected.get('registry')}"
        )
    return problems


def write_manifest_for(dest: Path, release: str | None) -> dict[str, Any]:
    """Measure an existing artifact and write its manifest: the path
    `--manifest-only` takes when the artifact to pin already exists (the
    bytes a release ships, never a fresh export)."""
    if not dest.is_file():
        raise FileNotFoundError(f"no demo artifact at {dest} to write a manifest for")
    manifest = build_manifest(dest, release)
    write_manifest(manifest, DEFAULT_MANIFEST)
    print(
        f"manifest: {DEFAULT_MANIFEST} (release {release or 'unpublished'},"
        f" artifact sha256 {manifest['artifact']['sha256']})"
    )
    return manifest


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Export the demo artifact and write its digest manifest (D-33, Amendment S)."
    )
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="write demo/demo.digest.json for the existing demo/demo.duckdb without exporting",
    )
    args = parser.parse_args(argv)
    release = os.environ.get(RELEASE_ENV_VAR) or None
    dest = DEFAULT_DEST
    if args.manifest_only:
        write_manifest_for(dest, release)
        return
    source = resolve_source_path()
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
    write_manifest_for(dest, release)


if __name__ == "__main__":
    main()
