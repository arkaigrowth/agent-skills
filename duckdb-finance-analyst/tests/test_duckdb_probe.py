"""Tests for scripts/duckdb_probe.py JSON contracts.

Exercises the probe helper against an in-memory DuckDB fixture and also runs the
CLI end to end against a temporary on-disk database, asserting the JSON shapes
the skill relies on.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "duckdb_probe.py"


def _load_probe_module():
    spec = importlib.util.spec_from_file_location("duckdb_probe", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


probe = _load_probe_module()


@pytest.fixture()
def conn():
    connection = duckdb.connect(":memory:")
    connection.execute(
        "CREATE TABLE transactions (id INTEGER, merchant_name VARCHAR, amount DOUBLE)"
    )
    connection.execute(
        "INSERT INTO transactions VALUES (1, 'Jane Doe Coffee', 4.50), (2, 'Acme Utilities', 88.10)"
    )
    connection.execute(
        "CREATE VIEW gold_spend_by_category AS SELECT merchant_name, SUM(amount) AS total FROM transactions GROUP BY merchant_name"
    )
    try:
        yield connection
    finally:
        connection.close()


def test_list_relations_contract(conn):
    relations = probe._list_relations(conn)
    assert isinstance(relations, list)
    assert relations, "expected at least one relation"
    for row in relations:
        assert set(row.keys()) == {"table_schema", "table_name", "table_type"}
    names = {row["table_name"] for row in relations}
    assert {"transactions", "gold_spend_by_category"} <= names
    types = {row["table_name"]: row["table_type"] for row in relations}
    assert types["transactions"] == "BASE TABLE"
    assert types["gold_spend_by_category"] == "VIEW"


def test_describe_relation_contract(conn):
    described = probe._describe_relation(conn, "transactions")
    assert isinstance(described, list)
    assert described, "expected column rows"
    for row in described:
        assert "column_name" in row
        assert "column_type" in row
    column_names = [row["column_name"] for row in described]
    assert column_names == ["id", "merchant_name", "amount"]


def test_run_query_contract(conn):
    result = probe._run_query(conn, "SELECT COUNT(*) AS n FROM transactions")
    assert set(result.keys()) == {"columns", "rows", "row_count"}
    assert result["columns"] == ["n"]
    assert result["row_count"] == 1
    assert result["rows"] == [{"n": 2}]


def test_run_query_is_json_serializable(conn):
    result = probe._run_query(conn, "SELECT id, merchant_name, amount FROM transactions ORDER BY id")
    encoded = json.dumps(result, default=str)
    decoded = json.loads(encoded)
    assert decoded["row_count"] == 2
    assert decoded["rows"][0]["merchant_name"] == "Jane Doe Coffee"


def _write_fixture_db(path: Path) -> None:
    connection = duckdb.connect(str(path))
    connection.execute("CREATE TABLE transactions (id INTEGER, amount DOUBLE)")
    connection.execute("INSERT INTO transactions VALUES (1, 10.0), (2, 20.0)")
    connection.close()


def test_cli_list_relations_json(tmp_path):
    db_path = tmp_path / "fixture.duckdb"
    _write_fixture_db(db_path)
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "list-relations", "--db", str(db_path)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert isinstance(payload, list)
    assert any(row["table_name"] == "transactions" for row in payload)


def test_cli_query_json(tmp_path):
    db_path = tmp_path / "fixture.duckdb"
    _write_fixture_db(db_path)
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "query",
            "--db",
            str(db_path),
            "--sql",
            "SELECT SUM(amount) AS total FROM transactions",
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["columns"] == ["total"]
    assert payload["row_count"] == 1
    assert payload["rows"] == [{"total": 30.0}]


def test_cli_error_returns_nonzero(tmp_path):
    db_path = tmp_path / "fixture.duckdb"
    _write_fixture_db(db_path)
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "query",
            "--db",
            str(db_path),
            "--sql",
            "SELECT * FROM does_not_exist",
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert "duckdb_probe error" in completed.stderr
