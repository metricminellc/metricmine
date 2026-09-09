"""make doctor: the five-minute-path preflight, keyless and offline.

Part of the Arc 4 stable-release surface. A stranger on a fresh clone runs
`make doctor` (`uv run mm doctor` on Windows, D-42) and learns, before
anything builds, whether this machine can run the demo: the platform, the
interpreter, its TLS trust store, uv, the locked toolchain, dbt packages,
the demo artifact (fetched or built), and the two environment lines local
dbt lanes need
(the F-09 class), printed in the running shell's form. Read-only: nothing
is installed, written, or fetched.

Verdicts: PASS, WARN (the demo still runs, or the item is only needed for
the contract gates), FAIL (the demo path is broken). Exit 0 unless a FAIL.

Run through the venv so the locked environment is what gets measured:

    make doctor
    uv run mm doctor
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# The locked packages a demo run exercises; resolved versions are read from
# uv.lock at run time, so a lock refresh never edits this file.
LOCKED = ["dbt-core", "dbt-duckdb", "duckdb", "anthropic", "mcp", "airbyte", "ruff"]
DATACONTRACT_PIN = "1.0.12"
WINDOWS = platform.system() == "Windows"

results: list[tuple[str, str, str]] = []


def cmd(target: str) -> str:
    """The documented command for a target on this platform (D-42): the
    Makefile on macOS and Linux, the task entry point on Windows. The same
    one-line rule as metricmine.tasks.command; this file stays standard
    library so it runs before the package is trusted, and
    tests/test_doctor.py holds the two to each other."""
    return f"uv run mm {target}" if WINDOWS else f"make {target}"


def record(verdict: str, label: str, detail: str) -> None:
    results.append((verdict, label, detail))


def locked_versions() -> dict[str, str]:
    text = (REPO / "uv.lock").read_text(encoding="utf-8")
    found = {}
    for m in re.finditer(r'\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"', text):
        if m.group(1) in LOCKED:
            found[m.group(1)] = m.group(2)
    return found


def check_platform() -> None:
    # The supported matrix (D-42): macOS, Linux, and Windows x64. Windows on
    # Arm is outside it because the dbt parser ships no Windows Arm wheel;
    # WSL is the Linux path.
    system, machine = platform.system(), platform.machine()
    if system in ("Darwin", "Linux") or (system == "Windows" and machine == "AMD64"):
        record("PASS", "platform", f"{system} ({machine})")
    elif system == "Windows":
        record(
            "WARN",
            "platform",
            f"{system} ({machine}): the Windows path is x64 only (no Windows Arm"
            " wheel for the dbt parser); WSL runs the Linux path",
        )
    else:
        record(
            "WARN",
            "platform",
            f"{system}: outside the supported matrix (macOS, Linux, Windows x64)",
        )


def check_python() -> None:
    v = sys.version_info
    if (v.major, v.minor) == (3, 12):
        record("PASS", "python", platform.python_version())
    else:
        record("FAIL", "python", f"{platform.python_version()}: the project runs on 3.12 (.python-version)")


def check_trust_store() -> None:
    # Every download the demo path makes verifies against this interpreter's
    # TLS trust (F-58). A python.org framework CPython on macOS wires neither
    # an OpenSSL cafile nor a capath until its Install Certificates.command
    # has run, and loads no anchors at all. Windows reports no cafile and no
    # capath either, because ssl.SSLContext.load_default_certs reads the
    # system certificate store there before it ever consults those paths; the
    # anchor count is what separates that working machine from a bare one,
    # and it is never the sole test, because a capath-only machine loads zero
    # anchors by default and verifies fine. Read-only: no network call.
    paths = ssl.get_default_verify_paths()
    anchors = len(ssl.create_default_context().get_ca_certs())
    if paths.cafile is None and paths.capath is None and not anchors:
        record(
            "FAIL",
            "trust store",
            "no cafile, no capath, and no default anchors; on a python.org"
            " build run Install Certificates.command, or point SSL_CERT_FILE"
            " at a CA bundle, then rerun",
        )
        return
    source = paths.cafile or paths.capath or "the system certificate store"
    record("PASS", "trust store", f"{source}, {anchors} anchors")


def check_uv() -> None:
    # Under `uv run` the project venv leads PATH and carries a locked `uv`
    # PyPI package (an airbyte dependency), which is not the uv that manages
    # this checkout. uv exports its own path to the child as UV; prefer it.
    exe = os.environ.get("UV") or shutil.which("uv")
    if not exe:
        record("FAIL", "uv", "not on PATH; install uv, then rerun")
        return
    out = subprocess.run([exe, "--version"], capture_output=True, text=True)
    record("PASS", "uv", out.stdout.strip() or exe)


def check_locked() -> None:
    try:
        want = locked_versions()
    except FileNotFoundError:
        record("FAIL", "uv.lock", "missing; this is not a full checkout")
        return
    misses = []
    for pkg in LOCKED:
        try:
            have = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            misses.append(f"{pkg} not installed")
            continue
        if pkg in want and have != want[pkg]:
            misses.append(f"{pkg} {have} != locked {want[pkg]}")
    if misses:
        record("FAIL", "locked toolchain", "; ".join(misses) + " (run: uv sync)")
    else:
        summary = ", ".join(f"{p} {want.get(p, '?')}" for p in ("dbt-core", "dbt-duckdb", "duckdb"))
        record("PASS", "locked toolchain", summary + ", and the rest per uv.lock")


def check_dbt_packages() -> None:
    if (REPO / "transform" / "dbt_packages" / "dbt_utils").exists():
        record("PASS", "dbt packages", "transform/dbt_packages/dbt_utils present")
    else:
        record("WARN", "dbt packages", f"not installed yet; `{cmd('demo')}` runs dbt deps first")


def check_datacontract() -> None:
    exe = shutil.which("datacontract")
    if not exe:
        record(
            "WARN",
            "datacontract-cli",
            f"not on PATH; the demo runs without it, the contract gates need "
            f"{DATACONTRACT_PIN} (uv tool install 'datacontract-cli[duckdb]=={DATACONTRACT_PIN}')",
        )
        return
    out = subprocess.run([exe, "--version"], capture_output=True, text=True)
    version = (out.stdout or out.stderr).strip().split()[-1] if (out.stdout or out.stderr) else "?"
    if version == DATACONTRACT_PIN:
        record("PASS", "datacontract-cli", f"{version}, isolated tool")
    else:
        record("WARN", "datacontract-cli", f"{version} on PATH; the pinned gate runs {DATACONTRACT_PIN}")


def check_demo_artifact() -> None:
    import json

    import duckdb

    demo = REPO / "demo" / "demo.duckdb"
    manifest_path = REPO / "demo" / "demo.digest.json"
    if not manifest_path.exists():
        record("FAIL", "demo artifact", "demo/demo.digest.json missing; this is not a full checkout")
        return
    if not demo.exists():
        # The artifact is a release asset (D-03 Amendment S): absent from a
        # fresh clone by design; the manifest says whether one is published.
        release = json.loads(manifest_path.read_text(encoding="utf-8"))["artifact"].get("release")
        if release:
            record(
                "WARN",
                "demo artifact",
                f"not fetched; {cmd('demo-fetch')} restores the {release} asset,"
                f" or {cmd('demo')} builds it",
            )
        else:
            record(
                "WARN",
                "demo artifact",
                f"no published artifact for this tree; {cmd('demo')} builds it",
            )
        return
    try:
        con = duckdb.connect(str(demo), read_only=True)
        try:
            (tables,) = con.execute(
                "select count(*) from information_schema.tables"
                " where table_schema = 'gold'"
            ).fetchone()
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001 - any open failure is the finding
        record("FAIL", "demo artifact", f"cannot open read-only: {exc}")
        return
    if tables:
        record("PASS", "demo artifact", f"opens read-only, {tables} gold objects")
    else:
        record("FAIL", "demo artifact", "opens but carries no gold objects")


def print_env_exports() -> None:
    # The two absolute paths the local dbt lanes need (the F-09 class), in
    # the form the running shell takes: bash and zsh export lines on macOS
    # and Linux, $env: assignments in PowerShell on Windows (D-42).
    profiles = REPO / "transform"
    warehouse = REPO / "warehouse" / "metricmine.duckdb"
    print()
    if WINDOWS:
        print("Local dbt lanes need these two environment lines in every fresh")
        print("PowerShell (absolute paths; the F-09 class):")
        print(f'  $env:DBT_PROFILES_DIR = "{profiles}"')
        print(f'  $env:MM_WAREHOUSE_PATH = "{warehouse}"')
        return
    print("Local dbt lanes need these two exports in every fresh terminal")
    print("(absolute paths; the F-09 class):")
    print(f'  export DBT_PROFILES_DIR="{profiles}"')
    print(f'  export MM_WAREHOUSE_PATH="{warehouse}"')


def main() -> int:
    for check in (
        check_platform,
        check_python,
        check_trust_store,
        check_uv,
        check_locked,
        check_dbt_packages,
        check_datacontract,
        check_demo_artifact,
    ):
        check()
    width = max(len(label) for _, label, _ in results)
    for verdict, label, detail in results:
        print(f"{verdict:<4} {label:<{width}}  {detail}")
    fails = sum(1 for v, _, _ in results if v == "FAIL")
    warns = sum(1 for v, _, _ in results if v == "WARN")
    print(f"\ndoctor: {len(results)} checks, {fails} FAIL, {warns} WARN")
    print_env_exports()
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
