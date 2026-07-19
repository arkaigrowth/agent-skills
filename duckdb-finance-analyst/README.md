# DuckDB Finance Analyst

A read-first [Claude Code](https://docs.claude.com/en/docs/claude-code/skills)
skill for analyzing finance data in DuckDB and MotherDuck. It profiles schemas,
inspects tables and views, debugs ingestion and categorization, and runs bounded
analytical SQL without mutating your data.

## Why

Finance datasets (statements, ledgers, reconciliation exports) reward a careful,
read-only posture: inventory the schema, work from gold views down to raw
sources, and keep queries bounded. This skill encodes that workflow and ships a
small Python helper (`scripts/duckdb_probe.py`) that returns predictable JSON so
an agent can reason over structure before writing wide queries.

## What is in here

- `SKILL.md` - the installable skill definition (frontmatter plus workflow guidance).
- `scripts/duckdb_probe.py` - CLI helper: `list-relations`, `describe`, `query`, all emitting JSON.
- `references/example-schema.md` - an illustrative medallion-style finance schema.
- `references/query-recipes.md` - reusable finance and debugging query patterns.
- `tests/test_duckdb_probe.py` - contract tests for the helper's JSON output.

## Install

Requires Python 3.11+ and the DuckDB Python package:

```bash
pip install duckdb
```

To use it as a Claude Code skill, copy this folder into your skills directory
(for example `~/.claude/skills/duckdb-finance-analyst`).

## Usage

Point the helper at a DuckDB file (or a `md:<database>` MotherDuck target). The
examples below use the `$FINLAKE_DB` placeholder:

```bash
export FINLAKE_DB=./data/finance.duckdb

# List tables and views as JSON
python3 scripts/duckdb_probe.py list-relations --db "$FINLAKE_DB"

# Describe a relation's columns
python3 scripts/duckdb_probe.py describe --db "$FINLAKE_DB" --relation transactions

# Run a bounded, read-oriented query
python3 scripts/duckdb_probe.py query --db "$FINLAKE_DB" --sql "SELECT COUNT(*) FROM transactions"
```

Example `query` output:

```json
{
  "columns": ["n"],
  "rows": [{ "n": 2 }],
  "row_count": 1
}
```

## Running the tests

```bash
pip install duckdb pytest
python3 -m pytest tests/ -q
```

The tests build an in-memory DuckDB fixture and also drive the CLI end to end
against a temporary on-disk database, asserting the JSON contracts and the
non-zero exit code on a bad query.

## Limitations

- The helper opens local databases read-only when the file already exists. It is
  a convenience wrapper, not a sandbox: a `query` command runs whatever SQL you
  pass, so treat write-capable connections (new files, MotherDuck) with care.
- MotherDuck support is a thin pass-through and depends on credentials already
  configured in your environment. It is not exercised by the test suite.
- The schema in `references/example-schema.md` is an illustrative example, not a
  fixed contract. Adapt relation and column names to your own dataset.
- Developed and tested on macOS with DuckDB 1.3.x and Python 3.11.

## License

MIT. See the repository root `LICENSE`.
