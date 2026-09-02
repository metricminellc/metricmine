"""Prove the committed demo artifact is what this tree's pipeline produces.

Governing decision: D-33 (docs/decisions/decision-register.md).

Compares the freshly built working warehouse against the committed
demo/demo.duckdb at the CONTENT layer: the gold object sets match, every
gold table matches by row count, and every gold view matches by row count
and ordered content digest (the D-33 invariant; the typed view carries no
run lineage or audit columns, so its digest is stable across builds and
machines). Cell-level table equality is deliberately not asserted here:
context_registry.loaded_at and the captured_at columns are build-time
stamps, honest audit metadata that differs between any two builds by
design; export-time equality of whole rows is export_demo.verify's job
within one build. Byte sizes never enter (machine-dependent).

A gold content change that lands without its demo refresh goes red here,
and a stranger's clone is proven to serve exactly what the pipeline
builds. Run after a green `dbt build`; CI runs it in contract-gate after
gate two. Locally:

    uv run python scripts/check_demo_digest.py

No key, no network. Exit 0 on a full match, 1 on any mismatch, 2 when an
input is missing.
"""

from __future__ import annotations

import sys

# Private helpers imported deliberately: the ordering-keyed digest and the
# gold-object census are the probed D-33 mechanics, not re-derived here.
from metricmine.export_demo import (
    DEFAULT_DEST,
    GOLD_SCHEMA,
    _gold_tables,
    _gold_views,
    _ident,
    _view_digest,
    resolve_source_path,
)

import duckdb


def main() -> int:
    source = resolve_source_path()
    dest = DEFAULT_DEST
    if not source.exists():
        print(
            f"working warehouse not found at {source}; run the build first "
            "(make ingest, then dbt build)",
            file=sys.stderr,
        )
        return 2
    if not dest.exists():
        print(f"committed demo artifact not found at {dest}", file=sys.stderr)
        return 2

    failures = 0
    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{source}' AS src (READ_ONLY)")
        con.execute(f"ATTACH '{dest}' AS exp (READ_ONLY)")
        src_tables, exp_tables = _gold_tables(con, "src"), _gold_tables(con, "exp")
        src_views = [n for n, _ in _gold_views(con, "src")]
        exp_views = [n for n, _ in _gold_views(con, "exp")]
        if src_tables != exp_tables or src_views != exp_views:
            print(
                f"gold object sets differ: warehouse tables {src_tables} views "
                f"{src_views}; demo tables {exp_tables} views {exp_views}"
            )
            return 1
        for table in src_tables:
            rel = f"{_ident(GOLD_SCHEMA)}.{_ident(table)}"
            (src_count,) = con.execute(f"select count(*) from src.{rel}").fetchone()
            (exp_count,) = con.execute(f"select count(*) from exp.{rel}").fetchone()
            if src_count == exp_count:
                print(f"table {table}: {src_count} rows equal")
            else:
                failures += 1
                print(f"table {table}: FAIL (warehouse {src_count}, demo {exp_count})")
    finally:
        con.close()

    for view in src_views:
        src_count, src_digest = _view_digest(source, view)
        exp_count, exp_digest = _view_digest(dest, view)
        if (src_count, src_digest) == (exp_count, exp_digest):
            print(f"view {view}: {src_count} rows, digest match ({src_digest})")
        else:
            failures += 1
            print(
                f"view {view}: FAIL (warehouse {src_count} rows {src_digest}, "
                f"demo {exp_count} rows {exp_digest})"
            )
    if failures:
        print(
            f"demo artifact drift: {failures} mismatch(es). If the gold content "
            "change is intended, refresh the artifact (make export-demo) and "
            "commit it in this pull request (D-33)."
        )
        return 1
    print("demo artifact matches the built warehouse content: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
