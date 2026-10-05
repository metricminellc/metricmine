"""`uv run mm driver`: register the pinned DuckDB engine as dbt's driver.

Governing decision: D-05 as amended by Amendment X (the dbt Core v2 move).
dbt v2 is a Rust engine that reaches every database through ADBC. Its pip
distribution ships no DuckDB driver: with nothing registered it looks for
a driver on the machine and then downloads one from the dbt Labs CDN,
whose DuckDB version this project does not pin. The project registers
its own instead. The `_duckdb` extension module inside the pinned Python
`duckdb` wheel exports the ADBC entrypoint `duckdb_adbc_init` (the
wheel's own `adbc_driver_duckdb` module names the same path and the same
entrypoint), so dbt writes the warehouse with the exact engine every
other part of the project opens it with, the file's storage version stays
the Python pin's by construction, and no CDN is reached.

The registration is an ADBC driver manifest, a small TOML file, in a
folder named by ADBC_DRIVER_PATH. The manifest carries an absolute path
(the ADBC driver manager accepts a relative one only behind a flag dbt
does not set), so it is written per clone and never committed: `.adbc/`
is gitignored. `uv run mm demo` and `make audit-gold` write it themselves
and pass ADBC_DRIVER_PATH to their dbt steps. A dbt line typed by hand
needs the export `uv run mm doctor` prints beside the two F-09 exports:

    uv run mm driver
    export ADBC_DRIVER_PATH="<repo>/.adbc"        (bash, zsh)
    $env:ADBC_DRIVER_PATH = "<repo>\\.adbc"        (PowerShell)

Standard library only, like the rest of the task entry point; the one
thing it reads is the location of the extension module in the project
venv, so it runs under `uv run`.
"""

from __future__ import annotations

import importlib.util
import platform
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DRIVER_DIR = REPO / ".adbc"
MANIFEST = DRIVER_DIR / "duckdb.toml"
ENV_VAR = "ADBC_DRIVER_PATH"
ENTRYPOINT = "duckdb_adbc_init"
MODULE = "_duckdb"


def engine_path() -> Path:
    """The extension module of the pinned duckdb wheel in this environment."""
    spec = importlib.util.find_spec(MODULE)
    if spec is None or not spec.origin:
        raise RuntimeError(
            "the duckdb wheel is not installed in this environment (run: uv sync)"
        )
    return Path(spec.origin)


def engine_version() -> str:
    return metadata.version("duckdb")


def _toml_string(value: str) -> str:
    # A TOML basic string: backslashes (Windows paths) and quotes escaped.
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def manifest_text(engine: Path, version: str) -> str:
    """The ADBC driver manifest for the pinned engine (manifest version 1)."""
    return (
        'name = "duckdb"\n'
        f"version = {_toml_string(version)}\n"
        'publisher = "metricmine: the engine inside the pinned Python duckdb wheel"\n'
        "\n"
        "[Driver]\n"
        f"shared = {_toml_string(str(engine))}\n"
        f'entrypoint = "{ENTRYPOINT}"\n'
    )


def write_manifest(driver_dir: Path = DRIVER_DIR) -> Path:
    """Write the manifest for this environment's engine; returns its path."""
    driver_dir.mkdir(parents=True, exist_ok=True)
    manifest = driver_dir / MANIFEST.name
    text = manifest_text(engine_path(), engine_version())
    if not manifest.exists() or manifest.read_text(encoding="utf-8") != text:
        manifest.write_text(text, encoding="utf-8", newline="\n")
    return manifest


def export_line(driver_dir: Path = DRIVER_DIR, windows: bool | None = None) -> str:
    """The environment line a hand-run dbt needs, in the running shell's form."""
    if platform.system() == "Windows" if windows is None else windows:
        return f'$env:{ENV_VAR} = "{driver_dir}"'
    return f'export {ENV_VAR}="{driver_dir}"'


def main() -> int:
    manifest = write_manifest()
    print(f"wrote {manifest}: duckdb {engine_version()} at {engine_path()}")
    print(f"dbt reads it when {ENV_VAR} names its folder: {export_line()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
