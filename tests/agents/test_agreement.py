"""The first-class agreement metric (D-25 touch, D-35): scoring scope.

Agreement scores only what the profile can evidence: per-column
first-class fields, presence and order, the grain tuple, rule type
shapes. Prose and provenance never move the score. Keyless.
"""

from __future__ import annotations

import copy

from metricmine.agents import agreement


def _document() -> dict:
    return {
        "id": "silver_example",
        "version": "1.1.0",
        "status": "active",
        "description": {"purpose": "p", "usage": "u", "limitations": "l"},
        "schema": [
            {
                "name": "silver_example",
                "properties": [
                    {
                        "name": "a",
                        "logicalType": "string",
                        "physicalType": "VARCHAR",
                        "required": True,
                        "primaryKey": True,
                        "primaryKeyPosition": 1,
                        "description": "prose",
                    },
                    {
                        "name": "b",
                        "logicalType": "integer",
                        "physicalType": "BIGINT",
                        "required": False,
                        "description": "prose",
                        "quality": [
                            {"type": "sql", "query": "q", "mustBe": 0}
                        ],
                    },
                ],
                "quality": [
                    {"type": "library", "metric": "rowCount"},
                    {"type": "sql", "query": "q", "mustBe": 0},
                ],
            }
        ],
    }


def test_identical_documents_agree_in_full() -> None:
    result = agreement.score(_document(), _document())
    assert result["first_class_checks"]["agree"] == 10
    assert result["first_class_checks"]["checked"] == 10
    assert result["columns"]["ordinal_order_equal"] is True
    assert result["grain"] == {
        "oracle": ["a"],
        "draft": ["a"],
        "set_equal": True,
        "order_equal": True,
    }
    assert result["rule_types"]["table_equal"] is True
    assert result["rule_types"]["column_equal"] is True
    assert result["mismatches"] == []


def test_prose_differences_never_move_the_score() -> None:
    draft = _document()
    draft["description"]["purpose"] = "entirely different prose"
    draft["status"] = "draft"
    draft["version"] = "9.9.9"
    draft["schema"][0]["properties"][0]["description"] = "other words"
    result = agreement.score(draft, _document())
    assert result["first_class_checks"]["agree"] == 10
    assert result["mismatches"] == []


def test_a_type_drift_is_one_named_mismatch() -> None:
    draft = _document()
    draft["schema"][0]["properties"][1]["physicalType"] = "INTEGER"
    result = agreement.score(draft, _document())
    assert result["first_class_checks"]["agree"] == 9
    assert result["mismatches"] == [
        "b.physicalType: oracle='BIGINT' draft='INTEGER'"
    ]


def test_a_missing_column_is_named_and_uncounted() -> None:
    draft = _document()
    draft["schema"][0]["properties"] = draft["schema"][0]["properties"][:1]
    result = agreement.score(draft, _document())
    assert result["columns"]["draft"] == 1
    assert result["first_class_checks"]["checked"] == 5
    assert "b: missing from the draft" in result["mismatches"]


def test_grain_order_scores_separately_from_the_set() -> None:
    oracle = _document()
    properties = oracle["schema"][0]["properties"]
    properties[1]["primaryKey"] = True
    properties[1]["primaryKeyPosition"] = 2
    draft = copy.deepcopy(oracle)
    draft_properties = draft["schema"][0]["properties"]
    draft_properties[0]["primaryKeyPosition"] = 2
    draft_properties[1]["primaryKeyPosition"] = 1
    result = agreement.score(draft, oracle)
    assert result["grain"]["set_equal"] is True
    assert result["grain"]["order_equal"] is False


def test_summary_lines_carry_the_study_frame() -> None:
    lines = agreement.summary_lines(agreement.score(_document(), _document()))
    assert lines[0].startswith("agreement study (n=1) against oracle")
    assert any("mismatches: none" in line for line in lines)
