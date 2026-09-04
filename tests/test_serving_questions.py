"""The demo question set, answered through the served path (Arc 6, D-41).

Local lane: needs the built warehouse (or MM_SERVE_DB pointing at a
built artifact). tests/fixtures/serving_questions.json is the question
set docs/demo.md hands a person testing the agent: each question, the
SQL that answers it on the typed surfaces, and the answer measured at
the committed samples. This test runs every SQL through
GoldWarehouse.query (the statement gate, the row cap, the JSON-native
rendering: the path a client takes) and holds the rows to the fixture,
so the expected answers in the demo guide are proven, not predicted.
It also checks that every registry claim a question leans on exists in
the expert context an agent would read first (Amendment W): the
cross-category join with its measured completeness, the vintage note
behind the PBI answer, and the null semantics behind the averages.

Serving exposes the gold schema only, and string values there are the
canonical lowercase text (D-18 as amended): the fixture's literals and
expected strings are lowercase on purpose.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from metricmine.query import ENV_VAR, GoldWarehouse

REPO = Path(__file__).resolve().parents[1]
WAREHOUSE = REPO / "warehouse" / "metricmine.duckdb"
FIXTURE = REPO / "tests" / "fixtures" / "serving_questions.json"

pytestmark = pytest.mark.local

QUESTIONS = json.loads(FIXTURE.read_text(encoding="utf-8"))["questions"]


@pytest.fixture(scope="module")
def gold():
    path = Path(os.environ.get(ENV_VAR) or os.environ.get("MM_WAREHOUSE_PATH") or WAREHOUSE)
    if not path.is_file():
        pytest.skip(f"no built warehouse at {path}")
    with GoldWarehouse(path) as warehouse:
        yield warehouse


@pytest.mark.parametrize("question", QUESTIONS, ids=[q["id"] for q in QUESTIONS])
def test_question_answers_as_documented(gold, question):
    result = gold.query(question["sql"], row_cap=100)
    assert result["truncated"] is False
    assert result["rows"] == question["expected_rows"], question["id"]


def test_every_question_names_a_served_category(gold):
    served = {c["category"] for c in gold.list_fact_categories()["categories"]}
    for question in QUESTIONS:
        assert set(question["categories"]) <= served, question["id"]
        for category in question["categories"]:
            assert f"mart_{category}_typed" in question["sql"], (
                f"{question['id']}: answered on the typed surface, never the star tables"
            )


def test_the_registry_carries_what_the_answers_lean_on(gold):
    """The knowledge the fixture's expert_context notes cite is present
    in the served registry, under expert_context, on the categories the
    question names."""
    listing = {c["category"]: c for c in gold.list_fact_categories()["categories"]}
    flights = gold.get_context(listing["flights"]["context_keys"]["dimensions"])["compiled_context"]
    weather = gold.get_context(listing["airport_weather"]["context_keys"]["measures"])["compiled_context"]
    retail = gold.get_context(listing["invoice_lines"]["context_keys"]["dimensions"])["compiled_context"]

    joins = flights["expert_context"]["cross_category_joins"]
    assert [j["name"] for j in joins] == ["flights_to_origin_weather"]
    assert joins[0]["measured_completeness"] == 0.9994
    assert "flights.origin_airport = airport_weather.airport_code" in joins[0]["join_condition"]
    assert joins == weather["expert_context"]["cross_category_joins"]

    assert "DJT" in flights["expert_context"]["limitations"]
    assert "decisionUnresolvedReferences" in flights["expert_context"]["decisions"]
    assert "null exactly when the flight is cancelled" in flights["expert_context"]["how_to_read"]
    assert "lowercase" in flights["data"]["value_form"]

    silver_joins = {j["name"]: j for j in flights["expert_context"]["joins"]}
    assert silver_joins["aircraft"]["measured_completeness"] == 0.8396

    assert "inches" in weather["expert_context"]["fields"]["precip_inches"]["meaning"]
    assert "10 is the reporting maximum" in weather["expert_context"]["fields"]["visibility_miles"]["meaning"]
    assert "12 airport-hours" in weather["expert_context"]["limitations"]

    assert "is_cancellation" in retail["expert_context"]["how_to_read"]
    assert retail["data"]["conformed_keys"] == {}
