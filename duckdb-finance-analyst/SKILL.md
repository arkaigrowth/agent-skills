---
name: duckdb-finance-analyst
description: Use when the user needs read-heavy DuckDB or MotherDuck analysis for finance, ledger, statement, reconciliation, tax, or Finlake data. Good for profiling schemas, inspecting tables/views, debugging ingestion or categorization, tracing lineage, summarizing spend, and running safe analytical SQL over local DuckDB databases or MotherDuck datasets.
---

# DuckDB Finance Analyst

Use this skill for structured finance analysis in DuckDB-backed datasets, especially:

- local DuckDB files with statements, exports, or ledgers
- MotherDuck datasets when credentials already exist
- monthly-close analysis over a finance data lake
- tax-oriented transaction review
- parser drift, reconciliation, or categorization debugging

Throughout this skill, "Finlake" is a running example name for a personal finance data lake. Substitute your own database name and paths.

Default posture:

- Prefer **read-only analysis**
- Start with **schema/profile** before deep SQL
- Prefer **gold views first**, then silver tables, then bronze/metadata only if debugging
- Keep queries bounded and explicit
- Distinguish facts from inferences

## When to Use

Use this skill when the user asks to:

- inspect a DuckDB or MotherDuck database
- profile financial data, accounts, statements, or exports
- analyze spend, income, transfers, or tax-relevant transactions
- debug ingestion, matching, categorization, or reporting in a finance data lake
- compare gold reports back to source rows with lineage

Do not use this skill for broad OCR/PDF extraction. Use it after data is already structured or when loading structured files into DuckDB for analysis.

## Core Workflow

### 1. Identify the Data Source

Before querying, state which source you are using:

- local DuckDB file path (this skill uses the `$FINLAKE_DB` environment variable or `./data/finance.duckdb` as the placeholder)
- `md:<database>` MotherDuck target
- local CSV/Parquet/XLSX loaded for temporary analysis

If using MotherDuck, say so explicitly in the response.

### 2. Inventory the Schema First

Use the bundled helper script for quick inspection:

```bash
python3 scripts/duckdb_probe.py list-relations --db "$FINLAKE_DB"
python3 scripts/duckdb_probe.py describe --db "$FINLAKE_DB" --relation transactions
```

For first-pass work, capture:

- relation names and types
- row counts for the key relations
- date range in the main fact table
- obvious null / uniqueness issues in important keys

### 3. Choose the Right Analysis Lane

Use one lane at a time:

- **Ledger / tax lane**: income, spend, transfers, deductions, account ownership
- **Reconciliation lane**: transaction to order / refund / allocation debugging
- **Categorization lane**: rules, overrides, source import, needs-review
- **Parser / ingestion lane**: row errors, duplicates, file lineage, drift

### 4. Run Bounded SQL

Use the helper for ad hoc queries:

```bash
python3 scripts/duckdb_probe.py query --db "$FINLAKE_DB" --sql "SELECT COUNT(*) FROM transactions"
```

Rules:

- Start with `COUNT(*)`, `LIMIT`, and grouped summaries before wide dumps
- Avoid `SELECT *` on large tables unless debugging a tiny filtered slice
- For tax work, aggregate first, then inspect representative rows
- When comparing systems, prefer a small reconciliation query plus a few sample rows

### 5. Report With Evidence

In your answer:

- name the relation(s) queried
- give the key counts/totals/date ranges
- label assumptions or uncertainty
- separate confirmed facts from likely interpretations

If you used provisional or noisy data, say so clearly.

## Finance Data Lake Lane

When working in a finance data lake, start here:

1. Read [references/example-schema.md](references/example-schema.md)
2. Inspect gold views first:
   - `gold_spend_by_category`
   - `gold_amazon_reconciliation`
   - `gold_needs_review`
3. Drop to silver only when needed:
   - `transactions`
   - `amazon_orders`
   - `amazon_items`
   - `amazon_refunds`
   - `allocations`
   - `classification_events`
   - `manual_overrides`
4. Use bronze / metadata only for debugging:
   - `bronze_*`
   - `ingestion_runs`
   - `source_files`
   - `row_errors`

For account/context questions, read whatever accounts reference and statement-pattern
docs ship alongside your own dataset. Keep those paths in local configuration rather
than hardcoding them here.

## MotherDuck Notes

MotherDuck is optional. Use it when:

- the user explicitly wants MotherDuck
- the dataset already lives there
- collaboration requires a shared hosted database

When using MotherDuck:

- connect only if credentials are already configured
- say explicitly that the analysis is running against MotherDuck
- profile relations before heavy scans
- keep exploratory queries tight and filtered

Do not assume MotherDuck is the source of truth if the local DuckDB file is the canonical build target.

## References

- [references/example-schema.md](references/example-schema.md): example query order and analysis targets for a finance data lake
- [references/query-recipes.md](references/query-recipes.md): reusable finance and debugging query patterns
