#!/usr/bin/env python3
"""Small read-oriented DuckDB/MotherDuck helper for finance analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb


def _connect(target: str, read_only: bool = True) -> duckdb.DuckDBPyConnection:
    if target.startswith("md:"):
        return duckdb.connect(target)

    path = Path(target).expanduser()
    if read_only and path.exists():
        return duckdb.connect(str(path), read_only=True)
    return duckdb.connect(str(path))


def _list_relations(conn: duckdb.DuckDBPyConnection) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY table_schema, table_name
        """
    ).fetchall()
    columns = [column[0] for column in conn.description]
    return [dict(zip(columns, row)) for row in rows]


def _describe_relation(conn: duckdb.DuckDBPyConnection, relation: str) -> list[dict[str, str | None]]:
    rows = conn.execute(f'DESCRIBE "{relation}"').fetchall()
    columns = [column[0] for column in conn.description]
    return [dict(zip(columns, row)) for row in rows]


def _run_query(conn: duckdb.DuckDBPyConnection, sql: str) -> dict[str, object]:
    rows = conn.execute(sql).fetchall()
    columns = [column[0] for column in conn.description]
    payload = [dict(zip(columns, row)) for row in rows]
    return {"columns": columns, "rows": payload, "row_count": len(payload)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-relations", help="List tables and views.")
    list_parser.add_argument("--db", required=True, help="DuckDB file path or md: URI.")

    describe_parser = subparsers.add_parser("describe", help="Describe a relation.")
    describe_parser.add_argument("--db", required=True, help="DuckDB file path or md: URI.")
    describe_parser.add_argument("--relation", required=True, help="Table or view name.")

    query_parser = subparsers.add_parser("query", help="Run a read-oriented SQL query.")
    query_parser.add_argument("--db", required=True, help="DuckDB file path or md: URI.")
    query_parser.add_argument("--sql", required=True, help="SQL query to execute.")

    args = parser.parse_args()

    try:
        with _connect(args.db) as conn:
            if args.command == "list-relations":
                print(json.dumps(_list_relations(conn), default=str, indent=2))
                return 0
            if args.command == "describe":
                print(json.dumps(_describe_relation(conn, args.relation), default=str, indent=2))
                return 0
            if args.command == "query":
                print(json.dumps(_run_query(conn, args.sql), default=str, indent=2))
                return 0
    except Exception as exc:  # pragma: no cover - operational helper
        print(f"duckdb_probe error: {exc}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
