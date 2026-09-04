"""The conformed-key gate (K1): conformance declared, typed, and enforced.

Arc 6 (D-41): conformance across sources is settled in silver and
declared at the contract plane, never modeled as shared dimensions in
gold. The star contract declares every conformed key with its physical
type and its normalization rule (`conformedKeyRules`, entries separated
by semicolons: `<key>=<TYPE>:<regex>`); each silver contract that carries
one names its columns (`conformedKeys`, entries `<column>=<key>` separated
by commas). This gate holds the declarations to each other:

- every key a silver contract names is declared in the star;
- every declared key is carried by at least two silver contracts, so a
  declaration is a join that exists, never decoration;
- every conformed column carries the declared physical type and is
  guarded by an error-severity SQL rule in its own contract whose query
  holds the column to the declared regex, so gate 3 runs the
  normalization on every build. A conformed column may be optional on
  the table that carries it (a flight with no reported aircraft); the
  rule then guards the non-null values and the registry says the key is
  nullable there.

CI-lane, keyless: contracts only. The same checks run over synthetic
contracts in a temp directory so the gate's refusals are proven.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
CONTRACTS = REPO / "contracts"
STAR = CONTRACTS / "gold_unified_event_star.odcs.yaml"


def _custom(contract: dict) -> dict[str, str]:
    return {
        entry["property"]: str(entry["value"])
        for entry in contract.get("customProperties", [])
    }


def parse_rules(star: dict) -> dict[str, tuple[str, str]]:
    """`key=TYPE:regex; key=TYPE:regex` to {key: (TYPE, regex)}."""
    raw = _custom(star).get("conformedKeyRules", "").strip()
    rules: dict[str, tuple[str, str]] = {}
    if not raw:
        return rules
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        key, _, rest = entry.partition("=")
        physical, _, regex = rest.partition(":")
        if not (key and physical and regex):
            raise ValueError(f"malformed conformedKeyRules entry: {entry!r}")
        rules[key.strip()] = (physical.strip(), regex.strip())
    return rules


def parse_keys(contract: dict) -> dict[str, str]:
    """`column=key, column=key` to {column: key}."""
    raw = _custom(contract).get("conformedKeys", "").strip()
    keys: dict[str, str] = {}
    if not raw:
        return keys
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        column, _, key = entry.partition("=")
        if not (column and key):
            raise ValueError(f"malformed conformedKeys entry: {entry!r}")
        keys[column.strip()] = key.strip()
    return keys


def _silver_contracts(directory: Path) -> list[tuple[Path, dict]]:
    found = []
    for path in sorted(directory.glob("*.odcs.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        obj = doc["schema"][0]
        if obj.get("physicalType") == "table" and str(obj.get("name", "")).startswith("silver_"):
            found.append((path, doc))
    return found


def check_gate(directory: Path, star: dict) -> list[str]:
    """Every violation, as one line each; empty means the gate holds."""
    rules = parse_rules(star)
    problems: list[str] = []
    carriers: dict[str, set[str]] = {key: set() for key in rules}
    for path, doc in _silver_contracts(directory):
        keys = parse_keys(doc)
        if not keys:
            continue
        obj = doc["schema"][0]
        columns = {prop["name"]: prop for prop in obj["properties"]}
        # ODCS carries quality at the table level and at the property level;
        # the normalization rule may sit at either.
        rule_sources = [obj] + list(obj["properties"])
        rule_queries = [
            str(rule.get("query", ""))
            for node in rule_sources
            for rule in (node.get("quality") or [])
            if rule.get("type") == "sql" and rule.get("severity") == "error"
            and rule.get("mustBe") == 0
        ]
        for column, key in keys.items():
            if key not in rules:
                problems.append(f"{path.name}: {column}={key} names an undeclared key")
                continue
            carriers[key].add(path.name)
            prop = columns.get(column)
            if prop is None:
                problems.append(f"{path.name}: conformed column {column} is not declared")
                continue
            physical, regex = rules[key]
            if prop.get("physicalType") != physical:
                problems.append(
                    f"{path.name}: {column} is {prop.get('physicalType')}, key {key} is {physical}"
                )
            guarded = any(
                column in query and regex in query for query in rule_queries
            )
            if not guarded:
                problems.append(
                    f"{path.name}: no error-severity rule holds {column} to {regex}"
                )
    for key, names in carriers.items():
        if len(names) < 2:
            problems.append(
                f"conformed key {key} is carried by {sorted(names)}; a conformed key joins"
                " at least two silver contracts"
            )
    return problems


def test_committed_contracts_pass_the_gate() -> None:
    star = yaml.safe_load(STAR.read_text(encoding="utf-8"))
    assert check_gate(CONTRACTS, star) == []


def _write(path: Path, doc: dict) -> None:
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _silver(name: str, columns: list[dict], keys: str, rules: list[dict]) -> dict:
    return {
        "id": name,
        "version": "1.0.0",
        "schema": [
            {
                "name": name,
                "physicalType": "table",
                "properties": columns,
                "quality": rules,
            }
        ],
        "customProperties": [{"property": "conformedKeys", "value": keys}],
    }


def _column(name: str, physical: str = "VARCHAR", required: bool = True) -> dict:
    return {"name": name, "physicalType": physical, "required": required}


def _regex_rule(table: str, column: str, regex: str) -> dict:
    return {
        "type": "sql",
        "severity": "error",
        "mustBe": 0,
        "query": f"SELECT COUNT(*) FROM silver.{table} WHERE NOT regexp_matches({column}, '{regex}')",
    }


@pytest.fixture
def star() -> dict:
    return {
        "customProperties": [
            {
                "property": "conformedKeyRules",
                "value": "airport_iata=VARCHAR:^[A-Z]{3}$; carrier_code=VARCHAR:^[A-Z0-9]{2,3}$",
            }
        ]
    }


def test_gate_accepts_a_conformed_pair(tmp_path, star) -> None:
    _write(
        tmp_path / "silver_a.odcs.yaml",
        _silver(
            "silver_a",
            [_column("origin")],
            "origin=airport_iata",
            [_regex_rule("silver_a", "origin", "^[A-Z]{3}$")],
        ),
    )
    _write(
        tmp_path / "silver_b.odcs.yaml",
        _silver(
            "silver_b",
            [_column("iata")],
            "iata=airport_iata",
            [_regex_rule("silver_b", "iata", "^[A-Z]{3}$")],
        ),
    )
    problems = check_gate(tmp_path, star)
    assert [p for p in problems if "airport_iata" in p and "at least two" in p] == []
    assert [p for p in problems if "silver_" in p] == []


def test_gate_refuses_decoration_type_drift_and_missing_rules(tmp_path, star) -> None:
    _write(
        tmp_path / "silver_a.odcs.yaml",
        _silver(
            "silver_a",
            [_column("origin", physical="INTEGER", required=False)],
            "origin=airport_iata, tail=aircraft",
            [],
        ),
    )
    problems = check_gate(tmp_path, star)
    joined = "\n".join(problems)
    assert "tail=aircraft names an undeclared key" in joined
    assert "origin is INTEGER, key airport_iata is VARCHAR" in joined
    assert "no error-severity rule holds origin to ^[A-Z]{3}$" in joined
    assert "conformed key airport_iata is carried by ['silver_a.odcs.yaml']" in joined
