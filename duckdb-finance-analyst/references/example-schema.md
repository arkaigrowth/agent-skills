# Example Finance Schema

This is an illustrative example schema for a finance data lake (referred to as
"Finlake" in this skill). It shows a medallion-style layout (bronze / silver /
gold) so the query-order guidance has something concrete to point at. Adapt the
relation names to your own database.

## Canonical Starting Point

Point the helper script at your database with the `$FINLAKE_DB` environment
variable, or use the `./data/finance.duckdb` placeholder:

```bash
export FINLAKE_DB=./data/finance.duckdb
python3 scripts/duckdb_probe.py list-relations --db "$FINLAKE_DB"
```

Keep connection bootstrap details (credentials, absolute paths) in local
configuration, not in this reference.

## Query Order

### Gold views first

- `gold_spend_by_category`
  - spend totals
  - category / subcategory coverage
  - uncategorized buckets
  - manual override vs rule vs source-import usage
- `gold_amazon_reconciliation`
  - matched / unmatched / excluded Amazon charges
  - allocation amounts
  - order linkage
- `gold_needs_review`
  - categorization items needing review

### Silver tables when gold is insufficient

- `transactions`
  - canonical card / cash transaction facts
  - key columns:
    - `transaction_date`
    - `account_name`
    - `institution`
    - `merchant_name`
    - `merchant_name_normalized`
    - `amount`
    - `source_category`
    - `ingestion_run_id`
    - `source_file_hash`
    - `row_hash`
- `amazon_orders`, `amazon_items`, `amazon_refunds`
  - order-level and item-level reconciliation evidence
- `match_candidates`, `allocations`, `match_runs`
  - scoring, status, and final allocation outputs
- `classification_events`, `categorization_runs`
  - category lineage and review status
- `manual_overrides`, `override_proposals`
  - human corrections and proposal flow

### Bronze and metadata only for debugging

- `bronze_transactions`
- `bronze_amazon_orders`
- `bronze_amazon_items`
- `bronze_amazon_refunds`
- `ingestion_runs`
- `source_files`
- `row_errors`

## High-Value Questions

### Tax-oriented

- what are total business-looking expenses by month
- what is still uncategorized
- which transactions carry `schedule_c_line` or `deduction_rate` hints
- what owner-draw / transfer patterns exist
- which accounts behave as business vs personal

### Pipeline-oriented

- why did a row fail parsing
- why is a transaction unmatched
- why is an item/category in needs review
- whether reruns are idempotent

## Design Notes

- local DuckDB is treated as the canonical target
- ambiguous Amazon matches should stay ambiguous
- every match / classification should preserve lineage
- real statements may be more trustworthy than scraped or inferred enrichment sources
