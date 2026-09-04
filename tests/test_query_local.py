"""Local-lane tests for the serving module against the built star.

Marked `local`: they need the gitignored warehouse that `make ingest` and
`dbt build` produce, so CI deselects them with -m "not local". Every
expectation is a measurement of the committed retail sample (the
44,721-line fact, the seven-field dimensions manifest), not a spec value;
the registry row count and the mapping version are read from the
committed artifacts so a new category or a contract bump never edits this
file (the multi-source fan-in, D-41). A new sample window changes the
measurements deliberately, with the contract.

Read-only throughout: the module opens the warehouse read_only and the
gate refuses anything that is not a SELECT, which the refusal cases here
exercise against the real connection rather than in isolation.
"""

import json
import re
from pathlib import Path

import pytest

from metricmine.query import ENV_VAR, GoldWarehouse, QueryRefused

_WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse" / "metricmine.duckdb"

# The dimensions schema key of the invoice_lines entity group, content-
# addressed at contract v1.1.0 (the country join, D-17's signature test).
DIMENSIONS_KEY = "2d27bd360b5092ff22047c65407ff05699afad98f455de2409665a5950a05e82"
# The measures schema key of the same group: the four-measure manifest.
MEASURES_KEY = "9dbc23cabca765eeaed72eb8161c90b5ae7857f81031656002f03e5bd9d99319"
UNKNOWN_KEY = "0" * 64

FACT_ROWS = 44721
DIMENSIONS_MANIFEST = [
    "invoice_id",
    "is_cancellation",
    "stock_code",
    "product_description",
    "customer_id",
    "country",
    "line_identity",
]

pytestmark = pytest.mark.local

_REPO = Path(__file__).resolve().parents[1]


def _registry_rows() -> int:
    from metricmine.engine.reader import load_compiled_context

    _version, compiled = load_compiled_context(_REPO)
    return len(compiled["entries"])


def _mapping_version() -> str:
    import yaml

    doc = yaml.safe_load(
        (_REPO / "contracts" / "gold_invoice_lines_mapping.odcs.yaml").read_text(
            encoding="utf-8"
        )
    )
    return doc["version"]


@pytest.fixture(scope="module")
def gold():
    if not _WAREHOUSE.is_file():
        pytest.skip(f"warehouse not built at {_WAREHOUSE}; run `make ingest` first")
    # MonkeyPatch.context() because the module-scoped fixture cannot take
    # the function-scoped `monkeypatch`; this exercises the same resolution
    # path a desktop client uses (spec §5).
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(ENV_VAR, str(_WAREHOUSE))
        with GoldWarehouse() as warehouse:
            yield warehouse


# --- list_fact_categories ---


MART_COLUMNS = [
    "invoice_id",
    "is_cancellation",
    "stock_code",
    "product_description",
    "customer_id",
    "country",
    "invoiced_at",
    "quantity",
    "unit_price",
    "fact_hash_id",
    "captured_at",
]


def test_lists_the_retail_category_with_its_row_count(gold):
    listed = gold.list_fact_categories()["categories"]
    by_name = {entry["category"]: entry for entry in listed}
    assert [entry["category"] for entry in listed] == sorted(by_name)
    assert by_name["invoice_lines"] == {
        "category": "invoice_lines",
        "fact_table": "fact_invoice_lines_values",
        "row_count": FACT_ROWS,
        "typed_table": "mart_invoice_lines_typed",
        "typed_columns": MART_COLUMNS,
        "query_hint": (
            "Ask questions against gold.mart_invoice_lines_typed"
            " (typed columns, one row per invoice_lines event)."
            " gold.fact_invoice_lines_values and the dim_* tables"
            " are the content-addressed provenance layer: hash keys"
            " and canonical JSON payloads, joined by hash, meant"
            " for lookup_record and audit, not for analytics."
            " String columns there carry canonical lowercase text:"
            " write literals in lowercase (origin_airport = 'jfk')."
            " get_context on the keys in context_keys returns what"
            " the columns are (data) and, kept apart by name, what"
            " the people who approved the contracts wrote about"
            " them (expert_context): units, vintages, nulls, joins."
        ),
        "subject": by_name["invoice_lines"]["subject"],
        "context_keys": {"dimensions": DIMENSIONS_KEY, "measures": MEASURES_KEY},
    }
    # Amendment W: the listing says what each category IS in the words of
    # the people who approved its contracts, and names the registry keys.
    assert len(by_name["invoice_lines"]["subject"]) > 40
    for entry in listed:
        assert entry["typed_table"] == f"mart_{entry['category']}_typed"
        assert entry["typed_columns"][-2:] == ["fact_hash_id", "captured_at"]
        assert entry["subject"], f"{entry['category']}: no subject in the listing"
        assert set(entry["context_keys"]) == {"dimensions", "measures"}
        for key in entry["context_keys"].values():
            context = gold.get_context(key)["compiled_context"]
            assert context["category"] == entry["category"]
            assert set(context) >= {"data", "expert_context"}


def test_mart_answers_the_typed_question_with_the_view_rows(gold):
    """The steer's promise measured: the mart and the view agree on a
    representative aggregate (D-36; the mart is the view's SELECT
    materialized lean)."""
    question = (
        "SELECT country, sum(quantity * unit_price) AS revenue FROM gold.{} "
        "GROUP BY country ORDER BY revenue DESC, country LIMIT 5"
    )
    mart = gold.query(question.format("mart_invoice_lines_typed"))
    view = gold.query(question.format("vw_invoice_lines_typed"))
    assert mart["rows"] == view["rows"]


# --- get_schema / get_context ---


def test_get_schema_returns_the_registry_declaration(gold):
    result = gold.get_schema(DIMENSIONS_KEY)
    assert result["found"] is True
    assert result["entity_group"] == "invoice_lines"
    assert result["contract_name"] == "gold_invoice_lines_mapping"
    assert result["contract_version"] == _mapping_version()
    assert result["role"] == "dimensions"
    assert result["manifest"] == DIMENSIONS_MANIFEST


def test_get_context_carries_the_compiled_field_descriptions(gold):
    result = gold.get_context(DIMENSIONS_KEY)
    assert result["found"] is True
    assert result["contract_name"] == "gold_invoice_lines_mapping"
    compiled = result["compiled_context"]
    # Amendment W: the typed declaration under data, the authored meaning
    # under expert_context, never the one inside the other.
    country = compiled["data"]["fields"]["country"]
    assert set(country) == {"logicalType", "mappingRole", "physicalType", "required"}
    meaning = compiled["expert_context"]["fields"]["country"]["meaning"]
    # The country field is the dimension the signature test added by
    # contract amendment alone; its description says so.
    assert "signature" in meaning.lower()
    assert compiled["expert_context"]["note"].startswith(
        "Authored knowledge, not a measurement"
    )


def test_unknown_schema_key_is_a_clean_empty_not_an_error(gold):
    schema = gold.get_schema(UNKNOWN_KEY)
    assert schema["found"] is False
    assert schema["entity_group"] is None
    assert schema["contract_name"] is None
    assert schema["contract_version"] is None
    assert schema["role"] is None
    assert schema["manifest"] is None
    context = gold.get_context(UNKNOWN_KEY)
    assert context["found"] is False
    assert context["compiled_context"] is None


# --- query: caps, truncation, JSON-native rendering, refusals ---


def test_query_caps_the_fact_and_announces_truncation(gold):
    result = gold.query("SELECT fact_hash_id FROM gold.fact_invoice_lines_values")
    assert result["row_count"] == 100
    assert result["truncated"] is True
    assert result["row_cap"] == 100
    assert len(result["rows"]) == 100


def test_query_under_the_cap_does_not_claim_truncation(gold):
    result = gold.query("SELECT * FROM gold.context_registry")
    assert result["row_count"] == _registry_rows()
    assert result["truncated"] is False


def test_query_returns_an_aggregate_as_one_row(gold):
    result = gold.query(
        "SELECT count(*) AS n FROM gold.fact_invoice_lines_values"
    )
    assert result["columns"] == ["n"]
    assert result["rows"] == [[FACT_ROWS]]
    assert result["truncated"] is False


def test_query_renders_decimal_and_timestamp_json_native(gold):
    result = gold.query(
        "SELECT unit_price, invoiced_at FROM gold.vw_invoice_lines_typed LIMIT 3"
    )
    assert result["row_count"] == 3
    for unit_price, invoiced_at in result["rows"]:
        # Decimal as str, not float: an exact price must not lose precision.
        assert isinstance(unit_price, str)
        assert isinstance(invoiced_at, str)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", invoiced_at)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM gold.context_registry",
        "SELECT 1; SELECT 2",
        "PRAGMA database_list",
    ],
    ids=["dml", "multi-statement", "pragma"],
)
def test_query_refuses_against_the_live_connection(gold, sql):
    with pytest.raises(QueryRefused):
        gold.query(sql)


# --- lookup_record: the provenance tool ---


@pytest.fixture(scope="module")
def sample_dim(gold):
    """One real dimension row, read through the module's own SELECT path."""
    result = gold.query(
        "SELECT dim_hash_id, dim_values FROM gold.dim_invoice_lines_values"
        " ORDER BY dim_hash_id LIMIT 1"
    )
    dim_hash_id, payload = result["rows"][0]
    return dim_hash_id, json.loads(payload)["line_identity"]


def test_lookup_finds_a_derived_identity_inside_the_payload(gold, sample_dim):
    dim_hash_id, line_identity = sample_dim
    result = gold.lookup_record(line_identity)
    assert result["found"] is True
    # A derived identity is reachable only through the JSON, so exactly one
    # place resolves it: the dimension payload it lives in.
    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["table"] == "dim_invoice_lines_values"
    assert "line_identity" in hit["column"]
    assert hit["match_count"] == 1
    assert hit["rows"][0]["dim_hash_id"] == dim_hash_id


def test_lookup_by_dim_hash_reaches_both_the_fact_and_the_dimension(gold, sample_dim):
    dim_hash_id, _line_identity = sample_dim
    result = gold.lookup_record(dim_hash_id)
    assert result["found"] is True
    found = {(hit["table"], hit["column"]): hit["match_count"] for hit in result["hits"]}
    assert found[("fact_invoice_lines_values", "dim_hash_id")] == 1
    assert found[("dim_invoice_lines_values", "dim_hash_id")] == 1


def test_lookup_by_schema_key_routes_to_the_registry(gold):
    result = gold.lookup_record(DIMENSIONS_KEY)
    assert result["found"] is True
    assert [(h["table"], h["column"]) for h in result["hits"]] == [
        ("context_registry", "schema_key")
    ]


def test_lookup_of_an_unknown_key_is_a_clean_empty(gold):
    result = gold.lookup_record(UNKNOWN_KEY)
    assert result["found"] is False
    assert result["hits"] == []
