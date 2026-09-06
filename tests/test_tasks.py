"""The task entry point (`uv run mm <target>`), statically, keyless (D-42).

The Makefile's demo-path targets delegate to src/metricmine/tasks.py so
the demo has one implementation on macOS, Linux, and Windows. This module
holds that implementation to the rules the Makefile used to be held to
(tests/agents/test_make_targets.py): the replay never invokes a proposer
(CLAUDE.md rule 17, D-24), the dbt lines follow the repo-root invocation
convention (D-11, D-20), and the connector venv is provisioned in the
platform's own layout. Nothing here spawns a process; the plan is computed
and inspected.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from metricmine import tasks

REPO_ROOT = Path(__file__).resolve().parents[1]
PROPOSER_MARKERS = ("metricmine.agents", "propose", "ANTHROPIC")


def _lines(steps: list[tasks.Step]) -> list[str]:
    return [" ".join(step.argv) for step in steps]


def test_the_entry_point_is_declared_and_carries_the_demo_path() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["scripts"] == {"mm": "metricmine.tasks:main"}
    assert tasks.TARGETS == (
        "doctor",
        "demo-fetch",
        "ingest",
        "demo",
        "export-demo",
        "demo-manifest",
    )


@pytest.mark.parametrize("target", tasks.TARGETS)
def test_no_target_reaches_a_proposer_or_the_key(target: str) -> None:
    for windows in (False, True):
        for line in _lines(tasks.plan(target, windows=windows)):
            for marker in PROPOSER_MARKERS:
                assert marker not in line, f"{target} reaches a proposer: {line!r}"


def test_demo_is_the_keyless_replay_in_order() -> None:
    lines = _lines(tasks.plan("demo", windows=False))
    assert lines[-3:] == [
        "uv run dbt deps --project-dir transform --profiles-dir transform",
        "uv run dbt build --project-dir transform --profiles-dir transform --target local",
        "uv run python -m metricmine.export_demo",
    ]
    assert "uv run python -m metricmine.ingest.land_sample" in lines


def test_dbt_lines_follow_the_repo_root_invocation_convention() -> None:
    for line in _lines(tasks.plan("demo")):
        if "dbt" in line:
            assert "--project-dir transform" in line
            assert "--profiles-dir transform" in line
    assert "--target local" in _lines(tasks.plan("demo"))[-2]


def test_connector_venv_follows_the_platform_layout() -> None:
    venv = Path("x") / ".venv-source-file"
    assert tasks.connector_python(venv, windows=True) == venv / "Scripts" / "python.exe"
    assert tasks.connector_executable(venv, windows=True) == venv / "Scripts" / "source-file.exe"
    assert tasks.connector_python(venv, windows=False) == venv / "bin" / "python"
    assert tasks.connector_executable(venv, windows=False) == venv / "bin" / "source-file"


@pytest.mark.parametrize("windows", [False, True])
def test_ingest_provisions_the_connector_venv_then_lands(windows: bool) -> None:
    steps = tasks.plan("ingest", windows=windows)
    executable = tasks.connector_executable(windows=windows)
    venv_step, install_step, land_step = steps
    assert venv_step.argv[:4] == ("uv", "venv", "--python", tasks.CONNECTOR_PYTHON)
    assert venv_step.skip_if_exists == executable
    assert install_step.argv[:3] == ("uv", "pip", "install")
    assert install_step.argv[3:5] == ("--python", str(tasks.connector_python(windows=windows)))
    assert install_step.argv[5:] == tasks.CONNECTOR_PACKAGES
    assert install_step.skip_if_exists == executable
    assert land_step.argv == ("uv", "run", "python", "-m", "metricmine.ingest.land_sample")
    assert land_step.skip_if_exists is None


def test_release_travels_as_the_exporter_environment() -> None:
    (step,) = tasks.plan("export-demo", release="v1.1.1")
    assert step.env == {"MM_DEMO_RELEASE": "v1.1.1"}
    (step,) = tasks.plan("demo-manifest")
    assert step.env == {"MM_DEMO_RELEASE": ""}
    assert step.argv[-1] == "--manifest-only"
    assert tasks.plan("demo", release="v1.1.1")[-1].env == {"MM_DEMO_RELEASE": "v1.1.1"}


def test_environment_is_a_dict_never_a_shell_prefix() -> None:
    for target in tasks.TARGETS:
        for step in tasks.plan(target):
            assert "=" not in step.argv[0]
            assert all("MM_DEMO_RELEASE" not in part for part in step.argv)


def test_the_uv_variable_wins_over_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UV", "/managed/uv")
    assert tasks.uv_binary() == "/managed/uv"
    monkeypatch.delenv("UV")
    monkeypatch.setattr(tasks.shutil, "which", lambda name: None)
    assert tasks.uv_binary() == "uv"


def test_unknown_target_refuses() -> None:
    with pytest.raises(ValueError):
        tasks.plan("propose-silver")
    with pytest.raises(ValueError):
        tasks.command("propose-silver")


@pytest.mark.parametrize("target", tasks.TARGETS)
def test_the_documented_command_follows_the_platform(target: str) -> None:
    assert tasks.command(target, windows=False) == f"make {target}"
    assert tasks.command(target, windows=True) == f"uv run mm {target}"


def test_the_documented_command_defaults_to_the_running_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tasks.sys, "platform", "win32")
    assert tasks.command("demo") == "uv run mm demo"
    monkeypatch.setattr(tasks.sys, "platform", "darwin")
    assert tasks.command("demo") == "make demo"

