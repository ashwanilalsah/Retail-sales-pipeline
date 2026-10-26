from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import mysql.connector
import pandas as pd

from src.config import DB_CONNECTION_ENABLED, get_db_config

LOGGER = logging.getLogger("retail_sales_pipeline.database")


def get_connection(config: dict[str, Any] | None = None):
    connection_config = config if config is not None else get_db_config()
    if connection_config.get("DB_CONNECTION_ENABLED", DB_CONNECTION_ENABLED) is not True:
        raise RuntimeError(
            "Database connections are disabled; explicitly set DB_CONNECTION_ENABLED=true "
            "for an authorized target"
        )
    return mysql.connector.connect(
        host=connection_config["DB_HOST"],
        port=int(connection_config["DB_PORT"]),
        user=connection_config["DB_USER"],
        password=connection_config["DB_PASSWORD"],
        database=connection_config["DB_NAME"],
        autocommit=False,
        connection_timeout=int(connection_config.get("DB_CONNECT_TIMEOUT", 10)),
    )


def execute_sql_file(connection, file_path: str | Path) -> None:
    path = Path(file_path)
    if path.suffix.lower() != ".sql":
        raise ValueError(f"Expected a .sql file: {path}")
    sql = path.read_text(encoding="utf-8")
    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
    cursor = connection.cursor()
    try:
        for statement in statements:
            cursor.execute(statement)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().date()
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _as_decimal(value: Any) -> Decimal:
    amount = Decimal(str(value))
    if not amount.is_finite():
        raise ValueError("Database load received a non-finite numeric value")
    return amount


def load_run_result(
    connection,
    run_metadata: dict[str, Any],
    accepted_records: Iterable[dict[str, Any]],
    rejected_records: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    accepted = list(accepted_records)
    rejected = list(rejected_records)
    input_count = int(run_metadata.get("input_count", len(accepted) + len(rejected)))
    accepted_count = int(run_metadata.get("accepted_count", len(accepted)))
    rejected_count = int(run_metadata.get("rejected_count", len(rejected)))
    duplicate_count = int(run_metadata.get("duplicate_count", 0))

    if accepted_count != len(accepted) or rejected_count != len(rejected):
        raise ValueError("Run metadata counts do not match supplied records")
    if input_count != accepted_count + rejected_count:
        raise ValueError("input_count must equal accepted_count plus rejected_count")
    if not run_metadata.get("run_id"):
        raise ValueError("run_metadata.run_id is required")
    source_file = Path(str(run_metadata.get("input_file", run_metadata.get("source_file", "unknown")))).name

    started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    cursor = connection.cursor()
    try:
        rows_inserted = 0
        rows_updated = 0
        rows_skipped = 0
        cursor.execute(
            """
            INSERT INTO etl_run_log
                (run_id, source_file, started_at, status, rows_read, rows_valid,
                 rows_rejected, rows_duplicates, rows_inserted, rows_updated, rows_skipped)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    source_file = VALUES(source_file),
                    started_at = VALUES(started_at),
                    finished_at = NULL,
                    status = VALUES(status),
                    rows_read = VALUES(rows_read),
                    rows_valid = VALUES(rows_valid),
                    rows_rejected = VALUES(rows_rejected),
                    rows_duplicates = VALUES(rows_duplicates),
                    rows_inserted = 0,
                    rows_updated = 0,
                    rows_skipped = 0
            """,
            (
                run_metadata["run_id"],
                source_file,
                started_at,
                "running",
                input_count,
                accepted_count,
                rejected_count,
                duplicate_count,
                rows_inserted,
                rows_updated,
                rows_skipped,
            ),
        )

        order_totals: dict[str, Decimal] = {}
        records_by_order: dict[str, dict[str, Any]] = {}
        for record in accepted:
            cursor.execute(
                """
                INSERT INTO customers (customer_id, customer_name)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE customer_name = VALUES(customer_name)
                """,
                (record["customer_id"], record["customer_name"]),
            )
            cursor.execute(
                """
                INSERT INTO products (product_id, product_name, category)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    product_name = VALUES(product_name),
                    category = VALUES(category)
                """,
                (record["product_id"], record["product_name"], record["category"]),
            )

            line_total = _as_decimal(record["total_amount"])
            order_id = str(record["order_id"])
            order_totals[order_id] = order_totals.get(order_id, Decimal("0")) + line_total
            records_by_order.setdefault(str(record["order_id"]), record)

        for order_id, record in records_by_order.items():
            cursor.execute(
                """
                INSERT INTO orders (order_id, customer_id, order_date, payment_method, order_total)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    customer_id = VALUES(customer_id),
                    order_date = VALUES(order_date),
                    payment_method = VALUES(payment_method),
                    order_total = VALUES(order_total)
                """,
                (
                    order_id,
                    record["customer_id"],
                    _as_date(record["order_date"]),
                    record["payment_method"],
                    order_totals[order_id],
                ),
            )
        for record in accepted:
            order_id = str(record["order_id"])
            cursor.execute(
                """
                INSERT INTO order_items
                    (order_id, product_id, quantity, unit_price, discount_percent, line_total)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    quantity = VALUES(quantity),
                    unit_price = VALUES(unit_price),
                    discount_percent = VALUES(discount_percent),
                    line_total = VALUES(line_total)
                """,
                (
                    order_id,
                    record["product_id"],
                    int(record["quantity"]),
                    _as_decimal(record["unit_price"]),
                    _as_decimal(record["discount_percent"]),
                    _as_decimal(record["total_amount"]),
                ),
            )
            row_count = cursor.rowcount
            if row_count == 1:
                rows_inserted += 1
            elif row_count == 2:
                rows_updated += 1
            elif row_count == 0:
                rows_skipped += 1

        for rejection in rejected:
            cursor.execute(
                """
                INSERT INTO rejected_records
                    (run_id, source_file, row_number, row_data, rejection_reasons)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    source_file = VALUES(source_file),
                    row_data = VALUES(row_data),
                    rejection_reasons = VALUES(rejection_reasons)
                """,
                (
                    run_metadata["run_id"],
                    source_file,
                    int(rejection["row_number"]),
                    json.dumps(rejection["record"], ensure_ascii=False, default=str, allow_nan=False),
                    json.dumps(rejection["reason_codes"], ensure_ascii=False, allow_nan=False),
                ),
            )

        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        cursor.execute(
            """
            UPDATE etl_run_log
            SET finished_at = %s, status = %s,
                rows_inserted = %s, rows_updated = %s, rows_skipped = %s
            WHERE run_id = %s
            """,
            (
                finished_at,
                "success",
                rows_inserted,
                rows_updated,
                rows_skipped,
                run_metadata["run_id"],
            ),
        )
        connection.commit()
    except Exception as exc:
        connection.rollback()
        LOGGER.error(
            "database_load_failed run_id=%s error_type=%s",
            run_metadata.get("run_id", "unknown"),
            type(exc).__name__,
        )
        raise
    finally:
        cursor.close()

    result = {
        "status": "success",
        "run_id": run_metadata["run_id"],
        "input_count": input_count,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "duplicate_count": duplicate_count,
        "orders_loaded": len(order_totals),
        "rows_inserted": rows_inserted,
        "rows_updated": rows_updated,
        "rows_skipped": rows_skipped,
    }
    LOGGER.info(
        "database_load_completed run_id=%s accepted_count=%d rejected_count=%d",
        result["run_id"],
        accepted_count,
        rejected_count,
    )
    return result


def load_run_outputs(run_metadata: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    cleaned_path = Path(run_metadata["cleaned_path"])
    rejected_path = Path(run_metadata["rejected_path"])
    accepted_df = pd.read_csv(cleaned_path, keep_default_na=False)
    accepted_records = accepted_df.to_dict(orient="records")
    rejected_records = json.loads(rejected_path.read_text(encoding="utf-8"))

    connection = get_connection(config)
    try:
        return load_run_result(connection, run_metadata, accepted_records, rejected_records)
    finally:
        connection.close()
