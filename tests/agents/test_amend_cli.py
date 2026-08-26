"""The amend CLI: refusal gates, the three governed inputs, the
direction summary (D-35).

Amend mirrors describe's refusal symmetry: describe refuses to shadow a
committed contract and points at amend; amend refuses an uncontracted
table and points at describe. The intent is required and non-empty
because an amendment without a stated intent has no governed reason to
exist (D-23 Amendment H). The happy path is exercised with run_proposer
stubbed, keyless.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from metricmine.agents import __main__ as cli
from metricmine.agents import harness

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def keyless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MM_PROPOSER_MODEL", raising=False)


def test_amend_requires_a_table(capsys: pytest.CaptureFixture) -> None:
    assert cli.main(["propose", "amend", "--intent", "x"]) == 1
    assert "requires --table" in capsys.readouterr().err


def test_amend_requires_a_non_empty_intent(
    capsys: pytest.CaptureFixture,
) -> None:
    code = cli.main(
        ["propose", "amend", "--table", "silver_invoice_lines"]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "non-empty --intent" in err
    assert "recorded verbatim" in err


def test_a_whitespace_intent_from_make_is_refused(
    capsys: pytest.CaptureFixture,
) -> None:
    code = cli.main(
        [
            "propose",
            "amend",
            "--table",
            "silver_invoice_lines",
            "--intent",
            "   ",
        ]
    )
    assert code == 1
    assert "non-empty --intent" in capsys.readouterr().err


def test_amend_refuses_an_uncontracted_table_and_points_at_describe(
    capsys: pytest.CaptureFixture,
) -> None:
    code = cli.main(
        [
            "propose",
            "amend",
            "--table",
            "silver_no_such_table",
            "--intent",
            "x",
        ]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "does not exist" in err
    assert "describe" in err
    assert "make propose-describe TABLE=silver_no_such_table" in err


def test_the_keyless_shell_is_refused_before_any_call(
    capsys: pytest.CaptureFixture,
) -> None:
    code = cli.main(
        [
            "propose",
            "amend",
            "--table",
            "silver_invoice_lines",
            "--intent",
            "correct the quantity description",
        ]
    )
    assert code == 1
    assert "ANTHROPIC_API_KEY is not set" in capsys.readouterr().err


def _stub_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict:
    """Stub run_proposer to a draft-written outcome carrying the example
    amend proposal, and capture the amend-specific arguments."""
    captured: dict = {}
    example = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "spec"
            / "agent-layer"
            / "example-amend-proposal.json"
        ).read_text(encoding="utf-8")
    )
    committed = yaml.safe_load(
        (REPO_ROOT / "contracts" / "silver_invoice_lines.odcs.yaml").read_text(
            encoding="utf-8"
        )
    )
    # Self-relative to the LIVE committed contract: the CLI reads
    # contracts/ directly, and the live version moves with every landed
    # amendment, so the expectations derive from the file, never from a
    # pinned literal.
    major, minor, patch = (int(x) for x in str(committed["version"]).split("."))
    captured["committed_version"] = str(committed["version"])
    captured["next_patch"] = f"{major}.{minor}.{patch + 1}"

    def fake_run_proposer(spec, repo_root, **kwargs):  # noqa: ANN001
        captured["intent"] = kwargs.get("intent")
        captured["extra_inputs"] = kwargs.get("extra_inputs")
        captured["provenance_extras"] = kwargs.get("provenance_extras")
        run_dir = tmp_path / "run"
        run_dir.mkdir(exist_ok=True)
        (run_dir / "proposal.json").write_text(
            json.dumps(example), encoding="utf-8"
        )
        draft = dict(committed)
        draft["version"] = captured["next_patch"]
        draft_path = run_dir / "draft.odcs.yaml"
        draft_path.write_text(yaml.safe_dump(draft), encoding="utf-8")
        report = kwargs["report"]
        report["run_dir"] = run_dir
        report["record"] = {"draft_path": str(draft_path)}
        return 0

    monkeypatch.setattr(cli.harness, "run_proposer", fake_run_proposer)
    return captured


def test_the_happy_path_binds_three_inputs_and_prints_the_direction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    captured = _stub_run(monkeypatch, tmp_path)
    code = cli.main(
        [
            "propose",
            "amend",
            "--table",
            "silver_invoice_lines",
            "--intent",
            "correct the quantity description",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert captured["intent"] == "correct the quantity description"
    bound, text = captured["extra_inputs"][0]
    assert bound.kind == "committed_contract"
    assert bound.path.endswith("contracts/silver_invoice_lines.odcs.yaml")
    assert bound.content_hash.startswith("sha256:")
    assert bound.schema_version == captured["committed_version"]
    assert "id: silver_invoice_lines" in text
    assert captured["provenance_extras"]["amendsContract"].startswith(
        f"silver_invoice_lines@{captured['committed_version']}#sha256:"
    )
    assert (
        "amendment direction: neutral; patch bump to "
        f"{captured['next_patch']} over {captured['committed_version']}"
        in out
    )
    assert "rule 6 warning" not in out


def test_a_narrowing_run_prints_the_rule_6_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    captured = _stub_run(monkeypatch, tmp_path)
    example_path = tmp_path / "run" / "proposal.json"

    def narrowing_stub(spec, repo_root, **kwargs):  # noqa: ANN001
        code = _original(spec, repo_root, **kwargs)
        proposal = json.loads(example_path.read_text(encoding="utf-8"))
        proposal["changes"].append(
            {
                "kind": "drop_column",
                "column": "product_description",
                "before": "VARCHAR",
                "after": "",
                "rationale": "operator intent",
            }
        )
        example_path.write_text(json.dumps(proposal), encoding="utf-8")
        return code

    _original = cli.harness.run_proposer
    monkeypatch.setattr(cli.harness, "run_proposer", narrowing_stub)
    code = cli.main(
        [
            "propose",
            "amend",
            "--table",
            "silver_invoice_lines",
            "--intent",
            "drop the description column",
            "--allow-relaxation",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert captured is not None
    assert "rule 6 warning" in out
    assert "NARROWS" in out


def test_the_operator_intent_governed_input_hashes_its_utf8_bytes() -> None:
    import hashlib

    intent = "correct the quantity description"
    expected = "sha256:" + hashlib.sha256(intent.encode("utf-8")).hexdigest()
    bound = harness.GovernedInput(
        kind="operator_intent",
        path="",
        content_hash=expected,
        schema_version="",
    )
    assert harness.recheck_inputs([bound]) == []
