"""D-34 model selection: precedence, allow-list refusal, rate rows.

Spec: docs/spec/agent-layer.md §1. Keyless; no client is ever built.
"""

from __future__ import annotations

import pytest

from metricmine.agents import models


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(models.ENV_VAR, raising=False)


def test_default_when_nothing_set() -> None:
    assert models.resolve_model(None) == models.Resolved(
        "claude-sonnet-5", "default"
    )


def test_env_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(models.ENV_VAR, "claude-opus-5")
    assert models.resolve_model(None) == models.Resolved(
        "claude-opus-5", "env"
    )


def test_flag_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(models.ENV_VAR, "claude-opus-5")
    assert models.resolve_model("claude-fable-5") == models.Resolved(
        "claude-fable-5", "flag"
    )


@pytest.mark.parametrize(
    "bad", ["latest", "claude-sonnet-latest", "claude-haiku-4-5", "gpt-5"]
)
def test_unlisted_id_refused_naming_the_allow_list(bad: str) -> None:
    with pytest.raises(models.ModelNotAllowedError) as excinfo:
        models.resolve_model(bad)
    message = str(excinfo.value)
    assert bad in message
    for allowed in models.MODELS:
        assert allowed in message


def test_unlisted_env_value_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(models.ENV_VAR, "latest")
    with pytest.raises(models.ModelNotAllowedError):
        models.resolve_model(None)


def test_cost_usd_at_each_rate_row() -> None:
    assert models.cost_usd("claude-sonnet-5", 1_000_000, 1_000_000) == (
        pytest.approx(12.00)
    )
    assert models.cost_usd("claude-opus-5", 500_000, 100_000) == (
        pytest.approx(5.00)
    )
    assert models.cost_usd("claude-fable-5", 100_000, 10_000) == (
        pytest.approx(1.50)
    )
