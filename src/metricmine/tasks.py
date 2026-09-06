"""`uv run mm <target>`: the task entry point the Makefile delegates to.

Governing decision: D-42 (supported platforms). `make <target>` is a
convenience layer over this module, so the demo path has one
implementation on macOS, Linux, and Windows and the two never diverge:
`make demo` on a Mac and `uv run mm demo` on Windows run the code below.
Standard library only; every command is a subprocess with its environment
passed as a dict, never a shell prefix, so the same lines run in bash,
zsh, PowerShell 7, and Windows PowerShell 5.1.

The targets, the demo path (D-42 scopes the entry point to it):

    uv run mm doctor                        the preflight (scripts/doctor.py)
    uv run mm demo-fetch                    restore and verify the release asset
    uv run mm ingest                        land the committed samples into bronze
    uv run mm demo [--release vX.Y.Z]       ingest, dbt deps, dbt build, export-demo
    uv run mm export-demo [--release vX.Y.Z]
    uv run mm demo-manifest [--release vX.Y.Z]

Every other `make <target>` in the repository's documents is a one-line
wrapper over a `uv run ...` command the Makefile shows; on Windows, run
that line. `--release` stamps the release the demo artifact ships with
(the Makefile's RELEASE=); unset means unpublished, as `make` has it.

`command(target)` is the documented form of a demo-path target on the
running platform (`make demo-fetch` on macOS and Linux, `uv run mm
demo-fetch` on Windows). Every hint the demo path prints names its remedy
through it (the fetch, the digest check, the exporter, the serving
module's fail-closed message), so no Windows reader is told to run
`make`; scripts/doctor.py, standard library by design, carries the same
one-line rule, and tests/test_tasks.py holds the two to each other.

The connector environment: PyPI's airbyte-source-file (0.3.15) pins
pandas==1.4.3, which only has wheels up to Python 3.10, so `ingest`
pre-provisions a CPython 3.10 venv for it with numpy<2 (the numpy 1.x
ABI pandas 1.4.3 was built against). PyAirbyte's ensure_installation()
sees the executable and skips its own installer. The venv's layout is the
platform's: `Scripts\\source-file.exe` on Windows, `bin/source-file`
elsewhere.

The keyless rule (CLAUDE.md rule 17, D-24): nothing here names a proposer,
the agents package, or the API key; tests/test_tasks.py holds the plan to
that.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CONNECTOR_VENV = REPO / ".venv-source-file"
CONNECTOR_PYTHON = "3.10"
CONNECTOR_PACKAGES = ("airbyte-source-file==0.3.15", "numpy<2")
RELEASE_ENV_VAR = "MM_DEMO_RELEASE"

# The dbt lines follow the repo-root invocation convention (D-11, D-20):
# the project and the profile are named explicitly, so the commands run
# from the repository root on every platform without an exported
# DBT_PROFILES_DIR.
DBT_DEPS = ("dbt", "deps", "--project-dir", "transform", "--profiles-dir", "transform")
DBT_BUILD = (
    "dbt",
    "build",
    "--project-dir",
    "transform",
    "--profiles-dir",
    "transform",
    "--target",
    "local",
)

TARGETS = ("doctor", "demo-fetch", "ingest", "demo", "export-demo", "demo-manifest")


def is_windows(platform: str | None = None) -> bool:
    return (platform or sys.platform) == "win32"


def uv_binary() -> str:
    """The uv that manages this checkout.

    Under `uv run` the project venv leads PATH and carries a locked `uv`
    PyPI package (an airbyte dependency) that is not the uv managing the
    checkout; uv exports its own path to the child as UV, so prefer it
    (the E-1 finding, scripts/doctor.py).
    """
    return os.environ.get("UV") or shutil.which("uv") or "uv"


def _windows(windows: bool | None) -> bool:
    return is_windows() if windows is None else windows


def command(target: str, windows: bool | None = None) -> str:
    """The documented form of a demo-path target on this platform (D-42):
    `make <target>` on macOS and Linux, `uv run mm <target>` on Windows.
    The hints the demo path prints name their remedy through this, so a
    reader is never told to run a tool the platform does not have."""
    if target not in TARGETS:
        raise ValueError(f"unknown target {target!r}; one of {', '.join(TARGETS)}")
    return f"uv run mm {target}" if _windows(windows) else f"make {target}"


def connector_python(venv: Path = CONNECTOR_VENV, windows: bool | None = None) -> Path:
    """The connector venv's interpreter in the platform's layout."""
    if _windows(windows):
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def connector_executable(venv: Path = CONNECTOR_VENV, windows: bool | None = None) -> Path:
    """The connector executable PyAirbyte looks for, in the platform's layout."""
    if _windows(windows):
        return venv / "Scripts" / "source-file.exe"
    return venv / "bin" / "source-file"


@dataclass(frozen=True)
class Step:
    """One subprocess: its argv, the environment it adds, and, for a
    provisioning step, the path whose presence makes it unnecessary."""

    argv: tuple[str, ...]
    env: dict[str, str] = field(default_factory=dict)
    skip_if_exists: Path | None = None


def release_env(release: str | None) -> dict[str, str]:
    """MM_DEMO_RELEASE for the exporter: the release named, or empty for
    unpublished, exactly as the Makefile's RELEASE= sets it."""
    return {RELEASE_ENV_VAR: release or ""}


def plan(
    target: str,
    release: str | None = None,
    windows: bool | None = None,
    uv: str = "uv",
) -> list[Step]:
    """The steps a target runs, in order, computed without running anything."""
    if target == "doctor":
        return [Step((uv, "run", "python", "scripts/doctor.py"))]
    if target == "demo-fetch":
        return [Step((uv, "run", "python", "scripts/fetch_demo.py"))]
    if target == "ingest":
        executable = connector_executable(windows=windows)
        return [
            Step(
                (uv, "venv", "--python", CONNECTOR_PYTHON, str(CONNECTOR_VENV)),
                skip_if_exists=executable,
            ),
            Step(
                (
                    uv,
                    "pip",
                    "install",
                    "--python",
                    str(connector_python(windows=windows)),
                    *CONNECTOR_PACKAGES,
                ),
                skip_if_exists=executable,
            ),
            Step((uv, "run", "python", "-m", "metricmine.ingest.land_sample")),
        ]
    if target == "export-demo":
        return [
            Step((uv, "run", "python", "-m", "metricmine.export_demo"), env=release_env(release))
        ]
    if target == "demo-manifest":
        return [
            Step(
                (uv, "run", "python", "-m", "metricmine.export_demo", "--manifest-only"),
                env=release_env(release),
            )
        ]
    if target == "demo":
        # The keyless replay (D-24; docs/demo.md Path B in one command):
        # land bronze, install the dbt packages, build the contracted
        # models, export the artifact. Never a proposer.
        return [
            *plan("ingest", windows=windows, uv=uv),
            Step((uv, "run", *DBT_DEPS)),
            Step((uv, "run", *DBT_BUILD)),
            *plan("export-demo", release=release, uv=uv),
        ]
    raise ValueError(f"unknown target {target!r}; one of {', '.join(TARGETS)}")


def execute(steps: list[Step]) -> int:
    """Run the steps in order from the repository root, echoing each
    command the way make echoes a recipe; stop at the first failure and
    return its exit code."""
    for step in steps:
        if step.skip_if_exists is not None and step.skip_if_exists.exists():
            continue
        print(" ".join(step.argv), flush=True)
        env = {**os.environ, **step.env}
        code = subprocess.run(list(step.argv), cwd=REPO, env=env).returncode
        if code:
            return code
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mm",
        description="The demo path, one implementation on every platform (D-42).",
    )
    parser.add_argument("target", choices=TARGETS, help="the target to run")
    parser.add_argument(
        "--release",
        default=os.environ.get(RELEASE_ENV_VAR) or None,
        metavar="vX.Y.Z",
        help="the release the demo artifact ships with (export-demo, demo-manifest, demo);"
        " unset means unpublished",
    )
    args = parser.parse_args(argv)
    return execute(plan(args.target, release=args.release, uv=uv_binary()))


if __name__ == "__main__":
    raise SystemExit(main())
