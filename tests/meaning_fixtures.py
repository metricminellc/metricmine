"""A miniature repository for the governed meaning tests (D-44).

The fixture is the demo's own vocabulary (nycflights13 and OurAirports,
in the steward's words): six terms, seven concepts, seven glossary
bindings, and four ontology bindings, the rows the Prep H probe
measured less the invoice line (D-44 names the two public sources, and
the retail sample is a third), so the digests the tests pin are the
probe transcript's. Every row is written by code from these builders;
nothing is typed twice.
"""

from __future__ import annotations

import datetime
import shutil
from pathlib import Path

import yaml

from metricmine.documents.commands import render_yaml
from metricmine.documents.register import sha256_text
from metricmine.meaning.changes import HEADERS
from metricmine.meaning.register import concept_digest, term_digest

REPO = Path(__file__).resolve().parents[1]
DAY = datetime.date(2026, 10, 26)
REVIEW = datetime.date(2027, 10, 26)
BY = "justinrgoff"

# The data contracts the demo's bindings name, with the columns they bind.
CONTRACTS = {
    "silver_flights": ["dep_delay_minutes", "arr_delay_minutes", "carrier_code", "tail_number", "origin_airport"],
    "silver_nyc_flights": ["dep_delay_minutes", "arr_delay_minutes", "carrier_code"],
    "silver_airport_weather": ["airport_ident", "temperature_c"],
    "silver_invoice_lines": ["invoice_no", "quantity"],
    "silver_ourairports_airports": ["airport_ident", "name"],
}


def term_row(**overrides) -> dict:
    row = {
        "term_id": "departure_delay",
        "term": "Departure delay",
        "definition": (
            "Minutes between the actual and the scheduled departure of a flight."
            " Negative when the flight left early. Absent when the flight was cancelled."
        ),
        "synonyms": "dep delay; dep_delay",
        "owner": "aviation stewards",
        "status": "active",
        "superseded_by": None,
        "declared_by": BY,
        "declared_on": DAY,
        "review_by": REVIEW,
    }
    row.update(overrides)
    return row


def concept_row(**overrides) -> dict:
    row = {
        "concept_id": "flight",
        "label": "Flight",
        "parent_id": None,
        "definition": "A scheduled movement of an aircraft from an origin airport to a destination airport.",
        "owner": "aviation stewards",
        "status": "active",
        "superseded_by": None,
        "declared_by": BY,
        "declared_on": DAY,
        "review_by": REVIEW,
    }
    row.update(overrides)
    return row


TERMS = [
    term_row(),
    term_row(
        term_id="arrival_delay", term="Arrival delay", synonyms="arr delay; arr_delay",
        definition=(
            "Minutes between the actual and the scheduled arrival of a flight. Negative when the flight"
            " arrived early. Absent when the flight was cancelled or no arrival was recorded."
        ),
    ),
    term_row(term_id="carrier", term="Carrier", synonyms="airline code; carrier code",
             definition="The airline operating a flight, identified by the two-character code its publisher assigns."),
    term_row(term_id="tail_number", term="Tail number", synonyms="tailnum; registration",
             definition="The registration painted on an aircraft's tail, which identifies the airframe across flights."),
    term_row(term_id="airport_ident", term="Airport identifier", synonyms="ident",
             definition=(
                 "The identifier OurAirports assigns to an airport, the ICAO code where one exists and a"
                 " local or generated code otherwise."
             )),
    term_row(term_id="cancellation", term="Cancellation", synonyms="cancelled flight",
             definition=(
                 "A scheduled departure that never departed. It keeps its row, carries no actual times and"
                 " no delays, and is counted from its flag."
             )),
]

CONCEPTS = [
    concept_row(),
    concept_row(concept_id="airport", label="Airport", definition="A place where aircraft take off and land, identified by a code."),
    concept_row(concept_id="aircraft", label="Aircraft", definition="An airframe identified by its registration."),
    concept_row(concept_id="weather_observation", label="Airport weather observation", parent_id="airport",
                definition="One hour of weather observed at an airport."),
    concept_row(concept_id="delay", label="Delay", parent_id="flight",
                definition="A difference between a flight's actual and scheduled time, in minutes."),
    concept_row(concept_id="departure_delay", label="Departure delay", parent_id="delay", definition="The delay measured at departure."),
    concept_row(concept_id="arrival_delay", label="Arrival delay", parent_id="delay", definition="The delay measured at arrival."),
]


def glossary_binding(term_id: str, contract_id: str, column_name: str, intent: str, terms: list[dict] | None = None, **overrides) -> dict:
    """A glossary binding at the term's current digest, as `bind` makes it."""
    rows = {r["term_id"]: r for r in (terms or TERMS)}
    row = {
        "term_id": term_id,
        "contract_id": contract_id,
        "column_name": column_name,
        "term_sha256": term_digest(rows[term_id]) if term_id in rows else "0" * 64,
        "intent": intent,
        "intent_sha256": sha256_text(intent),
        "bound_by": BY,
        "bound_on": DAY,
    }
    row.update(overrides)
    return row


def ontology_binding(concept_id: str, contract_id: str, column_name: str, intent: str, concepts: list[dict] | None = None, **overrides) -> dict:
    rows = {r["concept_id"]: r for r in (concepts or CONCEPTS)}
    row = {
        "concept_id": concept_id,
        "contract_id": contract_id,
        "column_name": column_name,
        "concept_sha256": concept_digest(rows[concept_id]) if concept_id in rows else "0" * 64,
        "intent": intent,
        "intent_sha256": sha256_text(intent),
        "bound_by": BY,
        "bound_on": DAY,
    }
    row.update(overrides)
    return row


GLOSSARY_BINDINGS = [
    glossary_binding("departure_delay", "silver_flights", "dep_delay_minutes", "dep_delay_minutes carries the departure delay term."),
    glossary_binding("arrival_delay", "silver_flights", "arr_delay_minutes", "arr_delay_minutes carries the arrival delay term."),
    glossary_binding("carrier", "silver_flights", "carrier_code", "carrier_code carries the carrier term."),
    glossary_binding("tail_number", "silver_flights", "tail_number", "tail_number carries the tail number term."),
    glossary_binding("cancellation", "silver_flights", "", "the unified flights table carries the cancellation term."),
    glossary_binding("departure_delay", "silver_nyc_flights", "dep_delay_minutes", "the level-zero table carries the same term."),
    glossary_binding("airport_ident", "silver_ourairports_airports", "airport_ident", "airport_ident carries the airport identifier term."),
]

ONTOLOGY_BINDINGS = [
    ontology_binding("flight", "silver_flights", "", "the unified flights table's entity type is Flight."),
    ontology_binding("weather_observation", "silver_airport_weather", "", "the airport weather table's entity type is Airport weather observation."),
    ontology_binding("departure_delay", "silver_flights", "dep_delay_minutes", "dep_delay_minutes carries the Departure delay concept."),
    ontology_binding("airport", "silver_ourairports_airports", "", "the airports reference table's entity type is Airport."),
]


def write_contracts(root: Path, contracts: dict[str, list[str]] | None = None, registers: bool = True) -> None:
    """The two register contracts copied from the repository, plus one
    small data contract per entry of `contracts`."""
    (root / "contracts").mkdir(parents=True, exist_ok=True)
    if registers:
        for name in ("glossary_register.odcs.yaml", "ontology_register.odcs.yaml"):
            shutil.copy(REPO / "contracts" / name, root / "contracts" / name)
    for cid, columns in (contracts if contracts is not None else CONTRACTS).items():
        (root / "contracts" / f"{cid}.odcs.yaml").write_text(
            yaml.safe_dump(
                {
                    "apiVersion": "v3.1.0",
                    "kind": "DataContract",
                    "id": cid,
                    "version": "1.0.0",
                    "schema": [{"name": cid, "physicalType": "table",
                                "properties": [{"name": c, "physicalType": "VARCHAR"} for c in columns]}],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )


def write_registers(root: Path, terms=None, glossary_bindings=None, concepts=None, ontology_bindings=None) -> None:
    """The four register files, rendered by the module's own dumper so a
    fixture reads as a rendering would. `None` means the demo rows."""
    terms = TERMS if terms is None else terms
    glossary_bindings = GLOSSARY_BINDINGS if glossary_bindings is None else glossary_bindings
    concepts = CONCEPTS if concepts is None else concepts
    ontology_bindings = ONTOLOGY_BINDINGS if ontology_bindings is None else ontology_bindings
    for folder, files in (
        ("glossary", (("terms.yaml", "terms", terms, "rows"), ("bindings.yaml", "bindings", glossary_bindings, "bindings"))),
        ("ontology", (("concepts.yaml", "concepts", concepts, "rows"), ("bindings.yaml", "bindings", ontology_bindings, "bindings"))),
    ):
        (root / "meaning" / folder).mkdir(parents=True, exist_ok=True)
        for file, key, rows, which in files:
            (root / "meaning" / folder / file).write_text(render_yaml(key, rows, HEADERS[(folder, which)]), encoding="utf-8")


def write_repo(root: Path, **registers) -> Path:
    """A repository under `root`: the contracts, the registers (the demo
    rows unless overridden), and the committed change-set schema."""
    write_contracts(root)
    write_registers(root, **registers)
    (root / "docs" / "spec" / "meaning").mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "docs" / "spec" / "meaning" / "change-set.schema.json", root / "docs" / "spec" / "meaning" / "change-set.schema.json")
    return root


def write_change_set(root: Path, name: str, changes: list[dict], by: str = BY,
                     intent: str = "the steward's words, verbatim.") -> Path:
    """A change-set file in the outbox, as a host's agent would write it."""
    folder = root / "proposals" / "meaning"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.changes.yaml"
    path.write_text(yaml.safe_dump({"by": by, "intent": intent, "changes": changes}, sort_keys=False), encoding="utf-8")
    return path


def load_rendered(out: Path, folder: str, file: str, key: str) -> list[dict]:
    return yaml.safe_load((out / folder / file).read_text(encoding="utf-8"))[key]
