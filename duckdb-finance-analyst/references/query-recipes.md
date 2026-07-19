# Query Recipes

Use these as patterns, not rigid templates.

## Relation inventory

```sql
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY table_schema, table_name;
```

## Row counts for key relations

```sql
SELECT 'transactions' AS relation, COUNT(*) AS n FROM transactions
UNION ALL
SELECT 'amazon_orders', COUNT(*) FROM amazon_orders
UNION ALL
SELECT 'amazon_items', COUNT(*) FROM amazon_items
UNION ALL
SELECT 'amazon_refunds', COUNT(*) FROM amazon_refunds;
```

## Date range check

```sql
SELECT MIN(transaction_date) AS min_date, MAX(transaction_date) AS max_date
FROM transactions;
```

## Monthly spend by category

```sql
SELECT
  DATE_TRUNC('month', transaction_date) AS month,
  category,
  subcategory,
  SUM(amount) AS total_amount,
  COUNT(*) AS transaction_count
FROM gold_spend_by_category
GROUP BY 1, 2, 3
ORDER BY month, total_amount DESC;
```

## Uncategorized / needs-review tail

```sql
SELECT
  transaction_date,
  institution,
  account_name,
  merchant_name,
  amount,
  category,
  subcategory,
  classification_source
FROM gold_spend_by_category
WHERE category = 'Uncategorized'
   OR subcategory = 'Needs Review'
ORDER BY ABS(amount) DESC
LIMIT 50;
```

## Parser drift / row errors

```sql
SELECT
  error_type,
  field,
  COUNT(*) AS n
FROM row_errors
GROUP BY 1, 2
ORDER BY n DESC, error_type, field;
```

## Match outcome summary

```sql
SELECT
  status,
  COUNT(*) AS n,
  SUM(allocated_amount) AS allocated_total
FROM allocations
GROUP BY 1
ORDER BY n DESC;
```

## Classification-source summary

```sql
SELECT
  classification_source,
  COUNT(*) AS n,
  SUM(amount) AS total_amount
FROM gold_spend_by_category
GROUP BY 1
ORDER BY n DESC;
```

## Business-rule metadata spot check

```sql
SELECT
  t.transaction_date,
  t.merchant_name,
  t.amount,
  ce.source,
  ce.output_json
FROM classification_events ce
JOIN transactions t
  ON ce.entity_type = 'transaction'
 AND ce.entity_id = t.id
ORDER BY t.transaction_date DESC
LIMIT 25;
```

## Transfer / counterparty investigation

```sql
SELECT
  transaction_date,
  account_name,
  merchant_name,
  description,
  amount,
  source_category
FROM transactions
WHERE lower(merchant_name) LIKE '%zelle%'
   OR lower(description) LIKE '%transfer%'
   OR lower(description) LIKE '%wire%'
ORDER BY transaction_date DESC
LIMIT 100;
```

