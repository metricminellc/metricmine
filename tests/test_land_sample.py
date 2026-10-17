"""Tests for the bronze landing (docs/spec/ingestion.md §5).

Two groups. The first is the unit surface of the temp-file shim (F-67):
PyAirbyte 0.53 makes each temporary file read-only and then retries its
deletion five times, one second apart, which Windows refuses; the landing
rebinds PyAirbyte's helper so the write bit comes back before the cleanup
runs. POSIX deletes a read-only file anyway, so a plain test cannot tell
the fixed code from the broken code here; these tests simulate Windows
semantics by making ``Path.unlink`` raise ``PermissionError`` while a
file lacks its owner write bit, and never assert on timing. They run in
the unit lane on every platform.

The second group is the local smoke test of the landing. Marked `local`:
it inspects the gitignored working warehouse that only `make ingest`
produces, so CI deselects it with -m "not local". It never runs the
pipeline itself; it asserts on the warehouse read-only, matching
acceptance criterion 3 (bronze is inspectable read-only).
"""

import os
import pathlib
import stat
import warnings
from pathlib import Path

import airbyte._connector_base as ab_connector_base
import airbyte._util.temp_files as ab_temp_files
import airbyte.sources.base as ab_sources_base
import duckdb
import pytest

from metricmine.ingest import land_sample

_WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse" / "metricmine.duckdb"

# What each rebinding target bound when this module was imported, before any
# fixture or test touched it: PyAirbyte's own helper on a pin the shim knows.
_BOUND_AT_IMPORT = tuple(
    getattr(module, "as_temp_files", None)
    for module in land_sample.TEMP_FILE_REBIND_TARGETS
)

# The committed sample's row count: data rows in
# data/samples/online_retail_ii/online_retail_ii_2009-12.csv (header excluded).
EXPECTED_ROWS = 45228


# --- the temp-file shim (F-67) ------------------------------------------


def _writable(path: str) -> bool:
    return bool(os.stat(path).st_mode & stat.S_IWUSR)


@pytest.fixture
def windows_unlink(monkeypatch):
    """Windows semantics on any platform: deleting a read-only file fails
    with WinError 5, surfaced by Python as PermissionError."""
    real_unlink = pathlib.Path.unlink

    def refuse_read_only(self, missing_ok=False):
        if self.exists() and not _writable(str(self)):
            raise PermissionError(13, "Access is denied", str(self))
        return real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(pathlib.Path, "unlink", refuse_read_only)


@pytest.fixture
def recorded_sleeps(monkeypatch):
    """Replace the ``time`` module PyAirbyte's helper sleeps through, so a
    retry shows up here as a recorded call instead of a second of wall
    clock."""
    sleeps: list[float] = []

    class _Time:
        @staticmethod
        def sleep(seconds: float) -> None:
            sleeps.append(seconds)

    monkeypatch.setattr(ab_temp_files, "time", _Time())
    return sleeps


@pytest.fixture
def unshimmed(monkeypatch):
    """Both rebinding targets restored to PyAirbyte's own helper for the
    test, whatever an earlier test or the module import left there."""
    original = ab_temp_files.as_temp_files
    for module in land_sample.TEMP_FILE_REBIND_TARGETS:
        monkeypatch.setattr(module, "as_temp_files", original)
    return original


def _run_helper(helper, caught: list) -> list[str]:
    """Open two temp files through ``helper`` (a dict for the JSON form, a
    string for the text form), record every warning, and return the paths
    after the context has closed."""
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        with helper([{"k": "v"}, "text"]) as paths:
            assert all(not _writable(p) for p in paths), "0.53 makes them read-only"
            kept = list(paths)
    caught.extend(str(w.message) for w in recorded)
    return kept


def _clean_up(paths: list[str]) -> None:
    for p in paths:
        if os.path.exists(p):
            os.chmod(p, 0o600)
            os.unlink(p)


def test_both_rebinding_targets_bound_pyairbytes_helper_at_import():
    # A PyAirbyte pin move that changes where the helper is bound fails
    # here first, loudly, instead of silently restoring the Windows cost.
    # The bindings are the ones this module saw at import, before any
    # fixture restored them.
    assert land_sample.TEMP_FILE_REBIND_TARGETS == (ab_sources_base, ab_connector_base)
    assert _BOUND_AT_IMPORT == (ab_temp_files.as_temp_files,) * 2


def test_every_call_site_of_the_helper_is_in_a_module_the_shim_knows():
    # The shim rebinds a name, so a call site PyAirbyte adds or moves in a
    # later release would keep the Windows cost without any other signal.
    # Every `as_temp_files(` call in the installed package must sit in a
    # module the shim rebinds or in the destinations module the landing
    # never uses.
    package = Path(ab_temp_files.__file__).resolve().parents[1]
    callers = set()
    for source in package.rglob("*.py"):
        for line in source.read_text(encoding="utf-8").splitlines():
            if "as_temp_files(" in line and not line.lstrip().startswith("def "):
                callers.add(source.relative_to(package).as_posix())
    assert callers == {"sources/base.py", "_connector_base.py", "destinations/base.py"}


def test_the_simulation_reproduces_the_windows_cost_without_the_shim(
    unshimmed, windows_unlink, recorded_sleeps
):
    # The instrument is checked before it is trusted: PyAirbyte's own
    # helper, under Windows semantics, sleeps four times per file, warns
    # once per file, and leaves both files behind.
    caught: list[str] = []
    paths = _run_helper(unshimmed, caught)
    try:
        assert recorded_sleeps == [1] * 8
        assert len(caught) == 2
        assert all(m.startswith("Failed to remove temporary file") for m in caught)
        assert all(os.path.exists(p) for p in paths)
    finally:
        _clean_up(paths)


def test_the_shim_deletes_every_temp_file_without_a_retry(
    unshimmed, windows_unlink, recorded_sleeps
):
    land_sample.install_temp_file_shim()
    caught: list[str] = []
    for module in land_sample.TEMP_FILE_REBIND_TARGETS:
        paths = _run_helper(module.as_temp_files, caught)
        try:
            assert recorded_sleeps == []
            assert caught == []
            assert not any(os.path.exists(p) for p in paths)
        finally:
            _clean_up(paths)


def test_the_shim_is_installed_once_and_only_over_pyairbytes_helper(unshimmed):
    land_sample.install_temp_file_shim()
    wrappers = [m.as_temp_files for m in land_sample.TEMP_FILE_REBIND_TARGETS]
    land_sample.install_temp_file_shim()
    assert [m.as_temp_files for m in land_sample.TEMP_FILE_REBIND_TARGETS] == wrappers
    assert all(w.wraps_as_temp_files is unshimmed for w in wrappers)
    # PyAirbyte's own module keeps its helper; only the call sites rebind.
    assert ab_temp_files.as_temp_files is unshimmed


def test_the_install_refuses_a_binding_it_does_not_recognize(unshimmed, monkeypatch):
    def not_pyairbytes(files_contents):
        raise AssertionError("never called")

    monkeypatch.setattr(ab_sources_base, "as_temp_files", not_pyairbytes)
    with pytest.raises(RuntimeError, match="F-67"):
        land_sample.install_temp_file_shim()


# --- the local smoke test of the landing ---------------------------------


@pytest.fixture(scope="module")
def bronze():
    if not _WAREHOUSE.is_file():
        pytest.skip(f"warehouse not built at {_WAREHOUSE}; run `make ingest` first")
    con = duckdb.connect(str(_WAREHOUSE), read_only=True)
    yield con
    con.close()


@pytest.mark.local
def test_bronze_table_exists(bronze):
    tables = {
        row[0]
        for row in bronze.execute(
            "select table_name from information_schema.tables"
            " where table_schema = 'bronze'"
        ).fetchall()
    }
    assert "online_retail_ii" in tables


@pytest.mark.local
def test_row_count_matches_committed_sample(bronze):
    (count,) = bronze.execute(
        "select count(*) from bronze.online_retail_ii"
    ).fetchone()
    assert count == EXPECTED_ROWS


@pytest.mark.local
def test_airbyte_metadata_columns_present(bronze):
    columns = {
        row[0]
        for row in bronze.execute(
            "select column_name from information_schema.columns"
            " where table_schema = 'bronze' and table_name = 'online_retail_ii'"
        ).fetchall()
    }
    assert {"_airbyte_raw_id", "_airbyte_extracted_at"} <= columns
