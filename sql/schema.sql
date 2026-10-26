CREATE DATABASE IF NOT EXISTS retail_sales_local CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE retail_sales_local;

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(64) PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(64) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR(64) NOT NULL,
    order_date DATE NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    order_total DECIMAL(14,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL,
    product_id VARCHAR(64) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    discount_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    line_total DECIMAL(12,2) NOT NULL,
    UNIQUE KEY uq_order_product (order_id, product_id),
    CONSTRAINT chk_order_items_quantity CHECK (quantity > 0),
    CONSTRAINT chk_order_items_unit_price CHECK (unit_price > 0),
    CONSTRAINT chk_order_items_discount CHECK (discount_percent >= 0 AND discount_percent <= 100),
    CONSTRAINT chk_order_items_line_total CHECK (line_total >= 0),
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(order_id),
    CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id VARCHAR(64) PRIMARY KEY,
    source_file VARCHAR(255) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP NULL,
    status VARCHAR(20) NOT NULL,
    rows_read INT NOT NULL DEFAULT 0,
    rows_valid INT NOT NULL DEFAULT 0,
    rows_rejected INT NOT NULL DEFAULT 0,
    rows_duplicates INT NOT NULL DEFAULT 0,
    rows_inserted INT NOT NULL DEFAULT 0,
    rows_updated INT NOT NULL DEFAULT 0,
    rows_skipped INT NOT NULL DEFAULT 0,
    notes TEXT NULL
);

CREATE TABLE IF NOT EXISTS rejected_records (
    rejection_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    row_number INT NOT NULL,
    row_data JSON NOT NULL,
    rejection_reasons JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_rejected_run_row (run_id, row_number),
    CONSTRAINT fk_rejected_run FOREIGN KEY (run_id) REFERENCES etl_run_log(run_id)
);

CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_products_category ON products(category);
