"""The preflight (`make doctor`, `uv run mm doctor` on Windows), statically.

scripts/doctor.py is standard library by design: it measures the environment
before the package is trusted, so it imports nothing from metricmine and
carries its own copy of the one-line command rule. These tests load it by
path and hold it to the register (D-42): the supported matrix and what sits
outside it, the environment lines in the running shell's form, and the
hints naming the same command the task entry point names, and the
trust-store check in each of its verdicts. Nothing here spawns a process
or reads the machine; every check under test is driven by a monkeypatched
`platform` or `ssl`. The pre-sync mode (the file run by a system Python
before `uv sync`) is held to reporting rather than raising.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

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


def _trust_store_verdict(
    monkeypatch: pytest.MonkeyPatch,
    cafile: str | None,
    capath: str | None,
    anchors: int,
    certifi_installed: bool = True,
) -> tuple[str, str, str]:
    paths = doctor.ssl.DefaultVerifyPaths(
        cafile, capath, "SSL_CERT_FILE", "openssl/cert.pem", "SSL_CERT_DIR", "openssl/certs"
    )
    monkeypatch.setattr(doctor.ssl, "get_default_verify_paths", lambda: paths)
    monkeypatch.setattr(
        doctor.ssl,
        "create_default_context",
        lambda *args, **kwargs: SimpleNamespace(get_ca_certs=lambda: [{}] * anchors),
    )
    if not certifi_installed:

        def absent(name: str) -> str:
            raise doctor.metadata.PackageNotFoundError(name)

        monkeypatch.setattr(doctor.metadata, "version", absent)
    monkeypatch.setattr(doctor, "results", [])
    doctor.check_trust_store()
    (entry,) = doctor.results
    return entry


def test_a_machine_with_no_trust_source_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    # A warning, not a failure, and the detail has to say why: metricmine.tls
    # adds certifi to whatever the machine trusts, so the demo path runs on a
    # bare store. FAIL would exit 1 into the devcontainer's postCreateCommand
    # and the demo-windows preflight, reddening a machine whose demo works.
    verdict, label, detail = _trust_store_verdict(monkeypatch, None, None, 0)
    assert (verdict, label) == ("WARN", "trust store")
    assert "the demo path carries its own CA bundle and runs" in detail
    assert "Install Certificates.command" in detail
    assert "SSL_CERT_FILE" in detail


def test_windows_loads_its_anchors_from_the_system_store_and_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Windows reports no cafile and no capath: ssl.SSLContext.load_default_certs
    # reads the system certificate store there before it consults either path.
    # Gating on the two paths alone would fail a working Windows machine, and
    # the demo-windows workflow runs this preflight.
    verdict, label, detail = _trust_store_verdict(monkeypatch, None, None, 168)
    assert (verdict, label) == ("PASS", "trust store")
    assert detail == "the system certificate store, 168 anchors"


def test_a_capath_only_machine_passes_with_no_anchors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The anchor count is never the sole test: a machine that resolves only a
    # capath loads zero anchors by default and verifies fine.
    verdict, label, detail = _trust_store_verdict(monkeypatch, None, "/etc/ssl/certs", 0)
    assert (verdict, label) == ("PASS", "trust store")
    assert detail == "/etc/ssl/certs, 0 anchors"


def test_a_cafile_that_parses_to_nothing_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    # The misconfiguration this check's own remedy invites: SSL_CERT_FILE
    # pointed at a file that exists and carries no certificates. Measured
    # against the repository README, it used to record PASS and silence the
    # warning without fixing anything.
    verdict, label, detail = _trust_store_verdict(monkeypatch, "README.md", None, 0)
    assert (verdict, label) == ("WARN", "trust store")
    assert "README.md loads no certificates" in detail


def test_an_unreadable_trust_store_warns_rather_than_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Reading the store reaches OpenSSL and, on Windows, the registry cert
    # stores. A raise would leave main() with a traceback and a non-zero
    # exit, which gates the devcontainer's postCreateCommand and the
    # demo-windows preflight: the FAIL outcome the WARN tier exists to avoid.
    def unreadable() -> None:
        raise OSError("cert store unavailable")

    monkeypatch.setattr(doctor.ssl, "get_default_verify_paths", unreadable)
    monkeypatch.setattr(doctor, "results", [])
    doctor.check_trust_store()
    (entry,) = doctor.results
    verdict, label, detail = entry
    assert (verdict, label) == ("WARN", "trust store")
    assert "cannot be read" in detail


def test_a_bare_store_with_no_certifi_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    # The usual warning tells the reader the demo path carries its own CA
    # bundle and runs. That is true only while certifi is installed; with no
    # store here and no bundle there a download verifies against nothing, and
    # the reassurance would be false right before the fetch fails.
    verdict, label, detail = _trust_store_verdict(
        monkeypatch, None, None, 0, certifi_installed=False
    )
    assert (verdict, label) == ("WARN", "trust store")
    assert "certifi is not installed" in detail
    assert "carries its own CA bundle and runs" not in detail


def test_before_uv_sync_the_artifact_check_reports_instead_of_raising(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The pre-sync form (`python3 scripts/doctor.py` on a system Python) has
    # no duckdb. Measured on a fresh clone before this guard: a traceback at
    # the import, exit 1, and not one check line printed.
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "demo.digest.json").write_text(
        '{"artifact": {"release": "v1.1.1"}}', encoding="utf-8"
    )
    (tmp_path / "demo" / "demo.duckdb").write_bytes(b"not a database")
    monkeypatch.setattr(doctor, "REPO", tmp_path)
    monkeypatch.setattr(doctor, "results", [])
    monkeypatch.setattr(doctor, "WINDOWS", False)
    monkeypatch.setitem(doctor.sys.modules, "duckdb", None)
    doctor.check_demo_artifact()
    (entry,) = doctor.results
    verdict, label, detail = entry
    assert (verdict, label) == ("WARN", "demo artifact")
    assert "duckdb is not importable here" in detail
    assert detail.endswith("run uv sync, then make doctor")


def test_before_uv_sync_the_locked_toolchain_names_the_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Under a system Python the locked packages are absent by definition;
    # that is not a broken demo path, it is a step not taken yet.
    monkeypatch.setattr(doctor, "IN_PROJECT_VENV", False)
    monkeypatch.setattr(doctor, "results", [])
    monkeypatch.setattr(doctor, "WINDOWS", True)
    doctor.check_locked()
    (entry,) = doctor.results
    verdict, label, detail = entry
    assert (verdict, label) == ("WARN", "locked toolchain")
    assert detail == "not measured yet: run uv sync, then uv run mm doctor"


def test_a_check_that_raises_records_a_fail_and_the_rest_still_print(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # main() prints after the last check, so an unhandled raise used to
    # discard every verdict already earned. A raise is now one FAIL line.
    def broken() -> None:
        raise RuntimeError("boom")

    def fine() -> None:
        doctor.record("PASS", "fine", "ok")

    monkeypatch.setattr(doctor, "CHECKS", (("fine", fine), ("broken", broken)))
    monkeypatch.setattr(doctor, "results", [])
    monkeypatch.setattr(doctor, "REPO", REPO_ROOT)
    assert doctor.main() == 1
    out = capsys.readouterr().out
    assert "PASS fine" in out
    assert "FAIL broken" in out and "RuntimeError: boom" in out
    assert "doctor: 2 checks, 1 FAIL, 0 WARN" in out


@pytest.mark.parametrize(("windows", "fix"), [(False, "make doctor"), (True, "uv run mm doctor")])
def test_a_python_off_the_pin_names_the_sync_that_provisions_it(
    monkeypatch: pytest.MonkeyPatch, windows: bool, fix: str
) -> None:
    # The pre-sync form runs on whatever Python the machine has. A 3.11 is
    # a FAIL for the interpreter, and the fix is the sync that provisions
    # the pinned 3.12, named in the shell's form like every other hint;
    # under uv run the venv's 3.12 is what answers, so the line never fires.
    monkeypatch.setattr(doctor.sys, "version_info", SimpleNamespace(major=3, minor=11, micro=15))
    monkeypatch.setattr(doctor.platform, "python_version", lambda: "3.11.15")
    monkeypatch.setattr(doctor, "WINDOWS", windows)
    monkeypatch.setattr(doctor, "results", [])
    doctor.check_python()
    (entry,) = doctor.results
    verdict, label, detail = entry
    assert (verdict, label) == ("FAIL", "python")
    assert detail == f"3.11.15: the project runs on 3.12 (.python-version); uv sync provisions it, then {fix}"
