"""Shared seams for the E3 tests (experiment branch; docs/experiments/e3/KEY.md).

A mirrored root links the committed inputs (profiles, contracts, prompts,
schemas, the experiment's own files) into a temporary directory and
copies the config, so the harness's outbox, the ledger, and the evidence
folder land under the temporary root and nothing in the clone moves.
The routing client answers by a key found inside the delimited payload
and never reaches a network; a queue entry that is an exception is
raised at the API seam, the way the SDK raises a transport error.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import httpx

import anthropic
from metricmine.agents import skeleton

REPO_ROOT = Path(__file__).resolve().parents[2]
LINKED = ("profiles", "contracts", "src", "docs", "tests")
RECORDED = REPO_ROOT / "tests" / "agents" / "fixtures" / "recorded"
E3 = REPO_ROOT / "docs" / "experiments" / "e3"
JUDGMENT_EXAMPLES = REPO_ROOT / "docs" / "spec" / "agent-layer" / "e3"
REQUEST = httpx.Request("POST", "https://x.invalid")


def mirrored_root(tmp_path: Path, name: str = "root") -> Path:
    root = tmp_path / name
    root.mkdir()
    for part in LINKED:
        (root / part).symlink_to(REPO_ROOT / part, target_is_directory=True)
    (root / "config").mkdir()
    shutil.copy(REPO_ROOT / "config" / "default.yaml", root / "config" / "default.yaml")
    return root


def response(text: str, *, input_tokens: int = 100, output_tokens: int = 50) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
        id="msg_fixture",
    )


class RoutingMessages:
    def __init__(self, outer: "RoutingClient") -> None:
        self._outer = outer

    def create(self, **kwargs: object) -> SimpleNamespace:
        self._outer.calls.append(kwargs)
        payload = kwargs["messages"][0]["content"]
        haystack = str(kwargs["system"]) + "\n" + payload
        for key, queue in self._outer.queues.items():
            needles = key if isinstance(key, tuple) else (key,)
            if all(needle in haystack for needle in needles):
                entry = queue.pop(0) if len(queue) > 1 else queue[0]
                if isinstance(entry, BaseException):
                    raise entry
                if callable(entry):
                    entry = entry()
                return response(entry)
        raise AssertionError(f"no route matches the payload: {payload[:80]}")


class RoutingClient:
    """Answers by a key (a substring, or a tuple of substrings that must all
    appear) inside the system prompt plus the delimited payload, first
    match wins; the last queue entry repeats so an always-failing route
    exhausts the retry budget."""

    def __init__(self, queues: dict[str, list]) -> None:
        self.queues = {key: list(entries) for key, entries in queues.items()}
        self.calls: list[dict] = []
        self.messages = RoutingMessages(self)


def connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=REQUEST)


def lint_ok(path: Path) -> tuple[bool, str]:
    return True, "lint ok"


def recorded(label: str) -> str:
    return (RECORDED / f"{label}.proposal.json").read_text(encoding="utf-8")


def profile(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def describe_judgment(artifact: dict, *, grain: list[str] | None = None) -> dict:
    """A minimal judgment over a profile: prose for every column, a grain
    of the first never-null column, no column rules, one decision."""
    columns = artifact["dataset"]["columns"]
    never_null = [c["name"] for c in columns if c["null_rate"] == 0.0]
    return {
        "stance": "describe",
        "column_prose": [
            {
                "name": c["name"],
                "description": f"The {c['name']} column as profiled.",
                "rationale": f"null_rate {c['null_rate']}, distinct_count {c.get('distinct_count')}.",
            }
            for c in columns
        ],
        "added_columns": [],
        "grain_keys": grain or never_null[:1],
        "quality_rules": [],
        "changes": [],
        "decisions": [
            {"key": "decisionGrainKeys", "value": "first-never-null", "rationale": "A test judgment."}
        ],
        "purpose": "A test purpose.",
        "usage": "A test usage.",
        "limitations": "A test limitation.",
    }


def describe_proposal(artifact: dict, judgment: dict | None = None) -> dict:
    """The full proposal head's describe stance would have to emit: the
    skeleton with the judgment applied, built here so the B-baseline
    fake answers with a complete, valid proposal."""
    judgment = judgment or describe_judgment(artifact)
    return skeleton.apply_judgment(skeleton.describe_skeleton(artifact), judgment)


def amend_judgment() -> dict:
    return json.loads(
        (JUDGMENT_EXAMPLES / "example-amend-judgment.json").read_text(encoding="utf-8")
    )


def amend_proposal(committed: dict, judgment: dict | None = None) -> dict:
    judgment = judgment or amend_judgment()
    return skeleton.apply_judgment(skeleton.amend_skeleton(committed), judgment)
