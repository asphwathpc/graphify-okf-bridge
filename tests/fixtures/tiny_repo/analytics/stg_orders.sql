-- Staging model: SQL-literal signal (INSERT INTO / FROM table identifiers).
INSERT INTO stg_orders
SELECT order_id, customer_id, total_usd, placed_at
FROM orders
WHERE status = 'completed'
