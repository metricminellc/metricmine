"""The E3 arms file, the context files, the leakage bar, and the dry path,
keyless (experiment branch; docs/experiments/e3/KEY.md Sections 2 to 5).

The baseline arm must run head's eval set literally: its fixtures equal
config's eleven on every field the eval lane reads. Every context file a
fixture names exists, passes the screen, and names no oracle-only column
(the leakage bar, Section 5). The dry path prints what each call would
carry for every arm with no call, byte-identical from two roots.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
import yaml

from metricmine.agents import e3, models
from metricmine.agents.harness import load_agents_config
from .e3_support import REPO_ROOT, mirrored_root

ARMS = e3.load_arms(REPO_ROOT)
HEAD_FIXTURES = load_agents_config(REPO_ROOT)["eval"]["fixtures"]
EVAL_KEYS = ("label", "proposer", "profile", "source", "table", "target", "oracle")


@pytest.fixture(autouse=True)
def _keyless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv(models.ENV_VAR, raising=False)


def test_the_baseline_arm_is_heads_eval_set_label_for_label() -> None:
    by_label = e3.fixtures_by_label(ARMS)
    assert ARMS["arms"]["baseline"]["fixtures"] == [f["label"] for f in HEAD_FIXTURES]
    for head in HEAD_FIXTURES:
        mine = by_label[head["label"]]
        for key in EVAL_KEYS:
            assert mine.get(key) == head.get(key), (head["label"], key)
    assert ARMS["arms"]["baseline"]["prompts"] == "head"
    assert ARMS["arms"]["baseline"]["context"] is False
    assert ARMS["arms"]["baseline"]["skeleton"] is False
    assert ARMS["arms"]["baseline"]["model_override"] is True


def test_every_arm_names_declared_fixtures_and_only_the_baseline_takes_a_model() -> None:
    by_label = e3.fixtures_by_label(ARMS)
    assert sorted(ARMS["arms"]) == ["A", "A0", "A1", "B", "B-baseline", "baseline"]
    assert ARMS["zero_fixtures"] == ["silver-cleanup-nyc-flights", "silver-cleanup-nyc-weather", "silver-cleanup-nyc-airlines"]
    assert ARMS["arms"]["A1"]["context"] == "docs_only" and ARMS["arms"]["A1"]["fixtures"] == ARMS["zero_fixtures"]
    assert ARMS["arms"]["A0"]["fixtures"] == ARMS["zero_fixtures"]
    for name, arm in ARMS["arms"].items():
        assert arm["repeats"] == 10, name
        for label in arm["fixtures"]:
            assert label in by_label, (name, label)
            fixture = by_label[label]
            if arm["context"]:
                assert e3.context_file(fixture, arm), (name, label)
            if arm["skeleton"]:
                assert fixture["stance"] in ("describe", "amend"), (name, label)
        if name != "baseline":
            assert arm["model_override"] is False, name
    assert ARMS["spend_bound_usd"] == 200.0
    assert ARMS["default_model"] == "claude-sonnet-5"
    for prompt_set in ("head", "e3"):
        for stance, rel in ARMS["prompts"][prompt_set].items():
            assert (REPO_ROOT / rel).is_file(), (prompt_set, stance)
    assert (REPO_ROOT / ARMS["judgment_schema"]).is_file()
    for fixture in ARMS["fixtures"]:
        assert float(fixture["estimate_usd"]) > 0, fixture["label"]
        assert (REPO_ROOT / fixture["profile"]).is_file(), fixture["label"]
        for key in ("oracle", "context", "context_docs_only", "committed"):
            if fixture.get(key):
                assert (REPO_ROOT / fixture[key]).is_file(), (fixture["label"], key)


def test_the_amend_fixture_binds_the_committed_before_contract_verbatim() -> None:
    fixture = e3.fixtures_by_label(ARMS)["amend-silver-invoice-lines-f28"]
    committed = yaml.safe_load((REPO_ROOT / fixture["committed"]).read_text(encoding="utf-8"))
    oracle = yaml.safe_load((REPO_ROOT / fixture["oracle"]).read_text(encoding="utf-8"))
    assert committed["id"] == oracle["id"] == "silver_invoice_lines"
    assert str(committed["version"]) == "1.2.0"
    assert str(oracle["version"]) == "1.3.0"
    before = next(p for p in committed["schema"][0]["properties"] if p["name"] == "captured_at")
    after = next(p for p in oracle["schema"][0]["properties"] if p["name"] == "captured_at")
    assert not before.get("required") and after.get("required") is True
    assert "captured_at" in fixture["intent"] and "Change nothing else" in fixture["intent"]


CONVENTIONS = (
    " We name a measure with its unit as a suffix (minutes, miles, mph, inches, degrees, feet, percent)."
    " We name a code column with `_code` and a boolean with `is_`."
    " We carry a calendar date as one DATE column rather than three integer parts."
    " We spell out abbreviated column names."
)


def test_context_files_pass_the_screen_and_carry_the_conventions_sentences() -> None:
    seen = 0
    for fixture in ARMS["fixtures"]:
        if not fixture.get("context"):
            continue
        text = (REPO_ROOT / fixture["context"]).read_bytes().decode("utf-8")
        refusals, dashes = e3.screen_text(text)
        assert refusals == [], fixture["label"]
        assert dashes == 0, fixture["label"]
        assert "\r" not in text and "<" not in text, fixture["label"]  # no tag can be forged
        assert text.endswith("\n"), fixture["label"]
        # The conventions sentences, in the operator's words: the four naming
        # sentences for the cleanup fixtures, the silver names kept for the
        # mapping fixtures.
        if fixture["stance"] == "cleanup":
            assert text.count(CONVENTIONS) == 1, fixture["label"]
        else:
            assert "We keep every field name as the silver contract names it." in text, fixture["label"]
        docs_only = fixture.get("context_docs_only")
        if docs_only:
            stripped = (REPO_ROOT / docs_only).read_bytes().decode("utf-8")
            assert stripped == text.replace(CONVENTIONS, ""), fixture["label"]
            seen += 1
    assert seen == 3


def test_the_leakage_bar_no_oracle_only_name_appears_in_any_context() -> None:
    out = io.StringIO()
    rows = e3.leakage(REPO_ROOT, out=out)
    assert len(rows) == 11  # eight contexts and the three docs-only variants
    assert sorted({r["label"] for r in rows}) == sorted(
        f["label"] for f in ARMS["fixtures"] if f.get("context") and f.get("oracle")
    )
    for row in rows:
        assert row["oracle_only_names_in_context"] == [], row
        assert row["context_chars"] > 0
        # Composition is the mechanism under test: the parts of a target
        # name are in the text and the conventions say how to join them.
        # It is reported, never hidden; the docs-only text composes fewer.
        assert isinstance(row["oracle_only_names_composable"], list)
    by_file = {r["file"]: r for r in rows}
    for label in ARMS["zero_fixtures"]:
        full = by_file[f"docs/experiments/e3/contexts/{label}.md"]
        docs = by_file[f"docs/experiments/e3/contexts/docs-only/{label}.md"]
        assert len(docs["oracle_only_names_composable"]) <= len(full["oracle_only_names_composable"]), label
    lines = out.getvalue().splitlines()
    assert len(lines) == 11 and all(line.startswith("LEAKAGE ") for line in lines)
    assert all("oracle-only names in the text 0;" in line for line in lines)
    assert all("composable from the text " in line for line in lines)


def _dry(root: Path, arm: str, **kwargs: object) -> tuple[int, str]:
    out = io.StringIO()
    code = e3.run_arm(root, arm, dry_run=True, out=out, **kwargs)
    return code, out.getvalue()


@pytest.mark.parametrize("arm", sorted(ARMS["arms"]))
def test_the_dry_path_prints_one_line_per_fixture_and_calls_nothing(tmp_path: Path, arm: str) -> None:
    root = mirrored_root(tmp_path)
    code, text = _dry(root, arm)
    assert code == 0, text
    lines = text.splitlines()
    assert lines[0].startswith("SPEND-BOUND 200.00 USD; ledger total 0.0000 USD; this batch: ")
    dry = [line for line in lines[1:] if line.startswith("DRY ")]
    assert len(dry) == len(ARMS["arms"][arm]["fixtures"]) == len(lines) - 1
    spec = ARMS["arms"][arm]
    for line, label in zip(dry, spec["fixtures"]):
        assert line.startswith(f"DRY {arm} {label}: ")
        assert "model=claude-sonnet-5" in line
        assert f"skeleton={'yes' if spec['skeleton'] else 'no'}" in line
        prompt = re.search(r"prompt=(\S+)@(\S+)", line)
        assert prompt is not None
        assert prompt.group(1).startswith("src/metricmine/agents/prompts/" + ("e3/" if spec["prompts"] == "e3" else ""))
        assert prompt.group(2) == ("1.1.0" if spec["prompts"] == "e3" else "1.0.0")
        tags = re.search(r"tags=(\S+)", line).group(1).split(",")
        assert tags[0] == "profile_artifact"
        assert (tags[-1] == "operator_context") == bool(spec["context"])
        assert ("context=-" in line) != bool(spec["context"])
    assert not (root / "proposals").exists()


def test_the_dry_path_is_byte_identical_from_two_roots(tmp_path: Path) -> None:
    one = mirrored_root(tmp_path, "one")
    two = mirrored_root(tmp_path, "two")
    for arm in sorted(ARMS["arms"]):
        assert _dry(one, arm) == _dry(two, arm), arm


def test_the_model_control_reruns_the_baseline_arm_only(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    code, text = _dry(root, "baseline", model_flag="claude-opus-5")
    assert code == 0
    assert "this batch: baseline claude-opus-5 110 runs" in text.splitlines()[0]
    assert all("model=claude-opus-5" in line for line in text.splitlines()[1:])
    for arm in ("A", "A0", "A1", "B", "B-baseline"):
        code, text = _dry(root, arm, model_flag="claude-opus-5")
        assert code == 1, arm
        assert text == ""


def test_batch_estimates_scale_by_the_rate_ratio(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    by_label = e3.fixtures_by_label(ARMS)
    for arm_name, arm in ARMS["arms"].items():
        expected = round(sum(float(by_label[label]["estimate_usd"]) for label in arm["fixtures"]) * 10, 4)
        _, text = _dry(root, arm_name)
        assert f"estimated {expected:.4f} USD" in text.splitlines()[0], arm_name
    _, text = _dry(root, "baseline", model_flag="claude-fable-5")
    base = round(sum(float(by_label[label]["estimate_usd"]) for label in ARMS["arms"]["baseline"]["fixtures"]) * 10, 4)
    assert f"estimated {round(base * 5.0, 4):.4f} USD" in text.splitlines()[0]
    assert e3.RATE_RATIO == {
        name: models.MODELS[name].input_per_mtok / models.MODELS["claude-sonnet-5"].input_per_mtok
        for name in models.MODELS
    }


def test_an_unknown_arm_or_a_bad_repeat_count_is_refused_before_any_call(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = mirrored_root(tmp_path)
    assert e3.run_arm(root, "C", dry_run=True, out=io.StringIO()) == 1
    assert "no arm 'C'" in capsys.readouterr().err
    assert e3.run_arm(root, "A", repeats=0, dry_run=True, out=io.StringIO()) == 1
    assert e3.run_arm(root, "A", out=io.StringIO()) == 1  # no key, no client: the live lane refuses
    err = capsys.readouterr().err
    assert "ANTHROPIC_API_KEY is not set" in err
    assert not (root / "proposals").exists()
