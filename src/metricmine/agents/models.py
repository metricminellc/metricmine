"""Proposer model selection: pinned default, allow-listed override (D-34).

Spec: docs/spec/agent-layer.md §1. The default model and the allow-list
live here in code by decision, never in config, so moving either is a
register amendment in its own documentation PR (rule 1 discipline).
Membership is measured, not preferred: an ID must support structured
outputs and the effort parameter, carry a pinned rate row here, and have
answered a live structured call on this project's account. Rates are USD
per million tokens, pinned at the August 22, 2026 published prices; a
price change is a rate-row edit under the same amendment discipline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

DEFAULT_MODEL = "claude-sonnet-5"
ENV_VAR = "MM_PROPOSER_MODEL"


@dataclass(frozen=True)
class Rates:
    input_per_mtok: float
    output_per_mtok: float


MODELS: Mapping[str, Rates] = MappingProxyType(
    {
        "claude-sonnet-5": Rates(2.00, 10.00),
        "claude-opus-5": Rates(5.00, 25.00),
        "claude-fable-5": Rates(10.00, 50.00),
    }
)


class ModelNotAllowedError(ValueError):
    """An ID outside the D-34 allow-list; aliases and `latest` included."""

    def __init__(self, model_id: str) -> None:
        allowed = ", ".join(sorted(MODELS))
        super().__init__(
            f"model {model_id!r} is not on the D-34 allow-list ({allowed}); "
            "adding a model is a register amendment in its own "
            "documentation PR"
        )


@dataclass(frozen=True)
class Resolved:
    model_id: str
    source: str  # "flag" | "env" | "default"


def resolve_model(flag: str | None) -> Resolved:
    """--model flag, then MM_PROPOSER_MODEL, then the default (D-34)."""
    if flag is not None:
        model_id, source = flag, "flag"
    elif env := os.environ.get(ENV_VAR):
        model_id, source = env, "env"
    else:
        model_id, source = DEFAULT_MODEL, "default"
    if model_id not in MODELS:
        raise ModelNotAllowedError(model_id)
    return Resolved(model_id=model_id, source=source)


def cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> float:
    rates = MODELS[model_id]
    return (
        input_tokens * rates.input_per_mtok / 1_000_000
        + output_tokens * rates.output_per_mtok / 1_000_000
    )
