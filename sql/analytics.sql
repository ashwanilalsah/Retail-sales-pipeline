USE retail_sales_local;

-- Overall performance: line revenue, orders, and average order value.
SELECT COALESCE(SUM(order_total), 0) AS total_revenue,
       COUNT(*) AS order_count,
       COALESCE(AVG(order_total), 0) AS average_order_value
FROM orders;

-- Monthly revenue and order volume.
SELECT DATE_FORMAT(order_date, '%Y-%m') AS month,
       SUM(order_total) AS monthly_revenue,
       COUNT(*) AS order_count
FROM orders
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY month;

-- Product revenue and units sold.
SELECT p.product_id,
       p.product_name,
       SUM(oi.line_total) AS revenue,
       SUM(oi.quantity) AS units_sold
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name
ORDER BY revenue DESC, p.product_id
LIMIT 10;

-- Revenue by category.
SELECT p.category,
       SUM(oi.line_total) AS revenue,
       SUM(oi.quantity) AS units_sold
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY revenue DESC, p.category;

-- Top customers by revenue and number of orders.
SELECT c.customer_id,
       c.customer_name,
       SUM(o.order_total) AS revenue,
       COUNT(*) AS order_count
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY revenue DESC, c.customer_id
LIMIT 10;

-- Revenue by payment method.
SELECT payment_method,
       SUM(order_total) AS revenue,
       COUNT(*) AS order_count
FROM orders
GROUP BY payment_method
ORDER BY revenue DESC, payment_method;

-- Rejected-record counts by stable reason code.
SELECT reasons.reason_code,
       COUNT(*) AS rejected_count
FROM rejected_records rr
JOIN JSON_TABLE(
    rr.rejection_reasons,
    '$[*]' COLUMNS (reason_code VARCHAR(100) PATH '$')
) AS reasons
GROUP BY reasons.reason_code
ORDER BY rejected_count DESC, reasons.reason_code;
