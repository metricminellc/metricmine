"""The dbt driver registration (`uv run mm driver`), statically (D-05 as amended).

dbt v2 reaches DuckDB through an ADBC driver. The project registers the
engine inside the pinned Python duckdb wheel by a manifest written under
.adbc/, so dbt writes the warehouse with the same engine the rest of the
project opens it with and no CDN is reached. These tests hold the manifest
to the ADBC driver manifest form, to an absolute path, to the pinned
wheel, and to the shell-neutral environment line.
"""

from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path

from metricmine import driver


def test_the_engine_is_the_pinned_wheels_extension_module() -> None:
    engine = driver.engine_path()
    assert engine.is_absolute() and engine.exists()
    assert engine.name.startswith("_duckdb.")
    assert driver.engine_version() == metadata.version("duckdb")


def test_the_manifest_is_valid_toml_in_the_adbc_form(tmp_path: Path) -> None:
    text = driver.manifest_text(tmp_path / "_duckdb.so", "1.4.3")
    manifest = tomllib.loads(text)
    assert manifest["name"] == "duckdb"
    assert manifest["version"] == "1.4.3"
    assert manifest["Driver"]["shared"] == str(tmp_path / "_duckdb.so")
    assert manifest["Driver"]["entrypoint"] == "duckdb_adbc_init"


def test_a_windows_path_survives_the_toml_string() -> None:
    engine = Path(r"C:\src\metricmine\.venv\Lib\site-packages\_duckdb.cp312-win_amd64.pyd")
    manifest = tomllib.loads(driver.manifest_text(engine, "1.4.3"))
    assert manifest["Driver"]["shared"] == str(engine)


def test_write_manifest_is_idempotent_and_names_this_environment(tmp_path: Path) -> None:
    first = driver.write_manifest(tmp_path / ".adbc")
    assert first == tmp_path / ".adbc" / "duckdb.toml"
    stamp = first.stat().st_mtime_ns
    second = driver.write_manifest(tmp_path / ".adbc")
    assert second == first and second.stat().st_mtime_ns == stamp
    manifest = tomllib.loads(first.read_text(encoding="utf-8"))
    assert manifest["Driver"]["shared"] == str(driver.engine_path())
    assert manifest["version"] == driver.engine_version()


def test_the_environment_line_takes_the_shells_form() -> None:
    folder = Path("/x/.adbc")
    assert driver.export_line(folder, windows=False) == 'export ADBC_DRIVER_PATH="/x/.adbc"'
    assert driver.export_line(folder, windows=True) == '$env:ADBC_DRIVER_PATH = "/x/.adbc"'
    assert driver.DRIVER_DIR == driver.REPO / ".adbc"
