USE retail_sales_local;

-- Static verification only: expected schema contract for the local ETL loader.
-- These checks validate the table/column names used by src/load.py and the
-- expected database contract defined in sql/schema.sql.

SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'retail_sales_local'
  AND TABLE_NAME IN (
    'customers',
    'products',
    'orders',
    'order_items',
    'etl_run_log',
    'rejected_records'
  )
ORDER BY TABLE_NAME, ORDINAL_POSITION;

SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'retail_sales_local'
  AND TABLE_NAME IN (
    'customers',
    'products',
    'orders',
    'order_items',
    'etl_run_log',
    'rejected_records'
  );

SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'retail_sales_local'
  AND TABLE_NAME IN (
    'orders',
    'order_items',
    'rejected_records'
  )
ORDER BY TABLE_NAME, COLUMN_NAME;

SELECT COUNT(*) AS customer_rows FROM customers;
SELECT COUNT(*) AS product_rows FROM products;
SELECT COUNT(*) AS order_rows FROM orders;
SELECT COUNT(*) AS order_item_rows FROM order_items;
SELECT COUNT(*) AS etl_run_rows FROM etl_run_log;
SELECT COUNT(*) AS rejected_rows FROM rejected_records;

-- Sanity check for loader assumptions: orders must have a valid order_total and
-- order_items must have nonzero quantities and positive prices.
SELECT COUNT(*) AS invalid_order_totals
FROM orders
WHERE order_total IS NULL OR order_total < 0;

SELECT COUNT(*) AS invalid_order_items
FROM order_items
WHERE quantity <= 0 OR unit_price <= 0 OR discount_percent < 0 OR discount_percent > 100;

-- Rejection metadata is expected to be stored as JSON arrays of reason codes.
SELECT COUNT(*) AS rejected_json_rows
FROM rejected_records
WHERE JSON_TYPE(rejection_reasons) NOT IN ('ARRAY', 'NULL');
