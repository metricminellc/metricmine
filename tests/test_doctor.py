"""The preflight (`make doctor`, `uv run mm doctor` on Windows), statically.

scripts/doctor.py is standard library by design: it measures the environment
before the package is trusted, so it imports nothing from metricmine and
carries its own copy of the one-line command rule. These tests load it by
path and hold it to the register (D-42): the supported matrix and what sits
outside it, the environment lines in the running shell's form, and the
hints naming the same command the task entry point names. Nothing here
spawns a process or reads the machine; every check under test is driven by
a monkeypatched `platform`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from metricmine import tasks

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_doctor():
    spec = importlib.util.spec_from_file_location("doctor", REPO_ROOT / "scripts" / "doctor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


doctor = _load_doctor()


def _platform_verdict(monkeypatch: pytest.MonkeyPatch, system: str, machine: str) -> tuple[str, str, str]:
    monkeypatch.setattr(doctor.platform, "system", lambda: system)
    monkeypatch.setattr(doctor.platform, "machine", lambda: machine)
    monkeypatch.setattr(doctor, "results", [])
    doctor.check_platform()
    (entry,) = doctor.results
    return entry


@pytest.mark.parametrize(
    ("system", "machine"),
    [("Darwin", "arm64"), ("Darwin", "x86_64"), ("Linux", "x86_64"), ("Linux", "aarch64"), ("Windows", "AMD64")],
)
def test_the_supported_matrix_passes(monkeypatch: pytest.MonkeyPatch, system: str, machine: str) -> None:
    verdict, label, detail = _platform_verdict(monkeypatch, system, machine)
    assert (verdict, label) == ("PASS", "platform")
    assert detail == f"{system} ({machine})"


def test_windows_on_arm_warns_with_the_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    verdict, label, detail = _platform_verdict(monkeypatch, "Windows", "ARM64")
    assert (verdict, label) == ("WARN", "platform")
    assert "x64 only" in detail
    assert "WSL" in detail


def test_outside_the_matrix_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    verdict, label, detail = _platform_verdict(monkeypatch, "FreeBSD", "amd64")
    assert (verdict, label) == ("WARN", "platform")
    assert "outside the supported matrix" in detail


@pytest.mark.parametrize("windows", [False, True])
def test_the_hints_name_the_same_command_as_the_entry_point(
    monkeypatch: pytest.MonkeyPatch, windows: bool
) -> None:
    monkeypatch.setattr(doctor, "WINDOWS", windows)
    for target in tasks.TARGETS:
        assert doctor.cmd(target) == tasks.command(target, windows=windows)


def test_the_environment_lines_take_the_running_shells_form(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(doctor, "WINDOWS", True)
    doctor.print_env_exports()
    windows_lines = capsys.readouterr().out
    assert '$env:DBT_PROFILES_DIR = "' in windows_lines
    assert '$env:MM_WAREHOUSE_PATH = "' in windows_lines
    assert "export " not in windows_lines
    monkeypatch.setattr(doctor, "WINDOWS", False)
    doctor.print_env_exports()
    posix_lines = capsys.readouterr().out
    assert 'export DBT_PROFILES_DIR="' in posix_lines
    assert 'export MM_WAREHOUSE_PATH="' in posix_lines
    assert "$env:" not in posix_lines


def test_the_demo_artifact_hint_names_the_fetch_and_the_build(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "demo.digest.json").write_text(
        '{"artifact": {"release": "v1.1.0"}}', encoding="utf-8"
    )
    monkeypatch.setattr(doctor, "REPO", tmp_path)
    monkeypatch.setattr(doctor, "results", [])
    monkeypatch.setattr(doctor, "WINDOWS", True)
    doctor.check_demo_artifact()
    (entry,) = doctor.results
    verdict, label, detail = entry
    assert (verdict, label) == ("WARN", "demo artifact")
    assert "uv run mm demo-fetch restores the v1.1.0 asset" in detail
    assert "uv run mm demo builds it" in detail
    assert "make " not in detail
