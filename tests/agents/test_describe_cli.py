"""The describe CLI: refusal gates and the oracle study path (D-35).

Describe refuses to shadow a committed contract, requires a table, and
under an explicit --oracle scores the draft and writes agreement.json
beside the record. All keyless: the refusals fire before any client
exists, and the oracle path is exercised with run_proposer stubbed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from metricmine.agents import __main__ as cli

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def keyless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MM_PROPOSER_MODEL", raising=False)


def test_describe_requires_a_table(capsys: pytest.CaptureFixture) -> None:
    assert cli.main(["propose", "describe"]) == 1
    assert "requires --table" in capsys.readouterr().err


def test_an_empty_table_from_make_is_refused(
    capsys: pytest.CaptureFixture,
) -> None:
    assert cli.main(["propose", "describe", "--table", ""]) == 1
    assert "requires --table" in capsys.readouterr().err


def test_describe_refuses_to_shadow_a_committed_contract(
    capsys: pytest.CaptureFixture,
) -> None:
    code = cli.main(
        ["propose", "describe", "--table", "silver_invoice_lines"]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "already exists" in err
    assert "amend" in err
    assert "ORACLE=contracts/silver_invoice_lines.odcs.yaml" in err


def test_a_missing_oracle_path_is_refused(
    capsys: pytest.CaptureFixture,
) -> None:
    code = cli.main(
        [
            "propose",
            "describe",
            "--table",
            "silver_invoice_lines",
            "--oracle",
            "contracts/no_such_contract.odcs.yaml",
        ]
    )
    assert code == 1
    assert "does not exist" in capsys.readouterr().err


def test_the_oracle_path_scores_and_writes_agreement_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    oracle_path = REPO_ROOT / "contracts" / "silver_invoice_lines.odcs.yaml"
    draft_path = tmp_path / "draft.odcs.yaml"
    draft_path.write_text(oracle_path.read_text(encoding="utf-8"))

    def fake_run_proposer(spec, repo_root, **kwargs):  # noqa: ANN001
        report = kwargs["report"]
        report["run_dir"] = tmp_path
        report["record"] = {"draft_path": str(draft_path)}
        return 0

    monkeypatch.setattr(cli.harness, "run_proposer", fake_run_proposer)
    code = cli.main(
        [
            "propose",
            "describe",
            "--table",
            "silver_invoice_lines",
            "--oracle",
            str(oracle_path),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "agreement study (n=1)" in out
    result = json.loads((tmp_path / "agreement.json").read_text())
    committed = yaml.safe_load(oracle_path.read_text(encoding="utf-8"))
    checks = len(committed["schema"][0]["properties"]) * 5
    assert result["first_class_checks"]["agree"] == checks
    assert result["mismatches"] == []


def test_a_failed_run_writes_no_agreement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oracle_path = REPO_ROOT / "contracts" / "silver_invoice_lines.odcs.yaml"

    def fake_run_proposer(spec, repo_root, **kwargs):  # noqa: ANN001
        return 2

    monkeypatch.setattr(cli.harness, "run_proposer", fake_run_proposer)
    code = cli.main(
        [
            "propose",
            "describe",
            "--table",
            "silver_invoice_lines",
            "--oracle",
            str(oracle_path),
        ]
    )
    assert code == 2
    assert not (tmp_path / "agreement.json").exists()
