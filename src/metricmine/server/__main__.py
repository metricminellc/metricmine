"""Entry point: `python -m metricmine.server` serves gold over stdio.

Spec: docs/spec/serving.md §7. No arguments and no configuration switches;
the served database is resolved by the query module from MM_SERVE_DB, then
the committed demo artifact (§5), so a desktop client configures this
server entirely through its environment.
"""

from __future__ import annotations

from metricmine.server.app import server


def _warm_native_imports() -> None:
    """Load the native modules DuckDB imports lazily on its first
    parameterized query, before the stdio transport parks its first stdin
    read (F-56, docs/spec/serving.md §7).

    DuckDB 1.4.3 evaluates `import_cache.pandas.NaT()` for every bound
    parameter, which imports pandas, and pandas pulls in numpy and
    pyarrow. On Windows numpy's bundled OpenBLAS DLL runs libgfortran's
    constructor during that import, which calls `fstat(0)`; the C runtime
    turns that into `PeekNamedPipe`, and Windows serializes it behind the
    SDK reader thread's already-pending `ReadFile` on the stdin pipe, so
    the first tool answer never arrives until the client sends another
    line (numpy issue 24290). Importing here, before `server.run` starts
    the reader, moves that load off the request path. About a quarter
    second, once, at startup; a module that is not installed is skipped,
    exactly as DuckDB's own guarded import would skip it.
    """
    import importlib

    for name in ("pandas", "numpy", "pyarrow"):
        try:
            importlib.import_module(name)
        except ImportError:
            pass


def main() -> None:
    _warm_native_imports()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
