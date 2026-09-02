"""make doctor: the five-minute-path preflight, keyless and offline.

Part of the Arc 4 stable-release surface. A stranger on a fresh clone runs
`make doctor` and learns, before anything builds, whether this machine can
run the demo: interpreter, uv, the locked toolchain, dbt packages, the
committed demo artifact, and the two environment exports local dbt lanes
need (the F-09 class). Read-only: nothing is installed, written, or fetched.

Verdicts: PASS, WARN (the demo still runs, or the item is only needed for
the contract gates), FAIL (the demo path is broken). Exit 0 unless a FAIL.

Run through the venv so the locked environment is what gets measured:

    make doctor
"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# The locked packages a demo run exercises; resolved versions are read from
# uv.lock at run time, so a lock refresh never edits this file.
LOCKED = ["dbt-core", "dbt-duckdb", "duckdb", "anthropic", "mcp", "airbyte", "ruff"]
DATACONTRACT_PIN = "1.0.12"

results: list[tuple[str, str, str]] = []


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
    system = platform.system()
    if system in ("Darwin", "Linux"):
        record("PASS", "platform", f"{system} ({platform.machine()})")
    else:
        record("WARN", "platform", f"{system}: outside the supported matrix (macOS, Linux)")


def check_python() -> None:
    v = sys.version_info
    if (v.major, v.minor) == (3, 12):
        record("PASS", "python", platform.python_version())
    else:
        record("FAIL", "python", f"{platform.python_version()}: the project runs on 3.12 (.python-version)")


def check_uv() -> None:
    exe = shutil.which("uv")
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
        record("WARN", "dbt packages", "not installed yet; `make demo` runs dbt deps first")


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
    import duckdb

    demo = REPO / "demo" / "demo.duckdb"
    if not demo.exists():
        record("FAIL", "demo artifact", "demo/demo.duckdb missing; this is not a full checkout")
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
    profiles = REPO / "transform"
    warehouse = REPO / "warehouse" / "metricmine.duckdb"
    print()
    print("Local dbt lanes need these two exports in every fresh terminal")
    print("(absolute paths; the F-09 class):")
    print(f'  export DBT_PROFILES_DIR="{profiles}"')
    print(f'  export MM_WAREHOUSE_PATH="{warehouse}"')


def main() -> int:
    for check in (
        check_platform,
        check_python,
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
