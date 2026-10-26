import ast
import json
import logging
from pathlib import Path

import pandas as pd
import pytest

from src.config import parse_bool, parse_db_port, parse_log_level
from src.logging_config import configure_logging
from src.transform import compute_line_total, normalize_record, standardize_dataframe
from src.validation import REQUIRED_COLUMNS

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_database_port_configuration_validation():
    assert parse_db_port("3306") == 3306
    for value in ("0", "65536", "not-a-port"):
        with pytest.raises(ValueError, match="DB_PORT"):
            parse_db_port(value)


def test_log_level_configuration_validation():
    assert parse_log_level("debug") == "DEBUG"
    with pytest.raises(ValueError, match="LOG_LEVEL"):
        parse_log_level("chatty")


def test_database_connection_switch_is_strict_and_off_by_default():
    assert parse_bool("DB_CONNECTION_ENABLED", "false") is False
    assert parse_bool("DB_CONNECTION_ENABLED", "TRUE") is True
    with pytest.raises(ValueError, match="DB_CONNECTION_ENABLED"):
        parse_bool("DB_CONNECTION_ENABLED", "yes")


def test_logging_is_structured_and_does_not_include_secrets(tmp_path):
    log_path = tmp_path / "pipeline.jsonl"
    logger = configure_logging(str(log_path), logging.INFO)
    try:
        logger.info("unit_test_event run_id=%s", "run-123")
        entry = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    finally:
        for handler in list(logger.handlers):
            if getattr(handler, "baseFilename", None) == str(log_path.resolve()):
                logger.removeHandler(handler)
                handler.close()

    assert entry["level"] == "INFO"
    assert "unit_test_event" in entry["message"]
    assert "password" not in entry
    assert "secret" not in entry


def test_transform_computes_line_total_and_standardizes_data():
    assert compute_line_total({
        "quantity": 2,
        "unit_price": 10,
        "discount_percent": 25,
    }) == 15
    frame = pd.DataFrame([{
        "order_id": " O-1 ",
        "customer_id": " C-1 ",
        "customer_name": " Ada ",
        "product_id": " P-1 ",
        "product_name": " Keyboard ",
        "category": " Electronics ",
        "order_date": "2024-03-02",
        "quantity": 2,
        "unit_price": 10,
        "discount_percent": 0,
        "total_amount": 20,
        "payment_method": " Card ",
    }], columns=REQUIRED_COLUMNS)

    standardized = standardize_dataframe(frame)

    assert standardized.iloc[0]["order_id"] == "O-1"
    assert standardized.iloc[0]["customer_name"] == "Ada"
    assert standardized.iloc[0]["order_date"] == pd.Timestamp("2024-03-02")


def test_normalize_record_preserves_large_whole_quantity_without_float_rounding():
    large_quantity = "100000000000000000001"
    assert normalize_record({"quantity": large_quantity})["quantity"] == int(large_quantity)
    with pytest.raises(ValueError, match="whole number"):
        normalize_record({"quantity": "1.5"})


def test_analytics_queries_reference_schema_tables_and_rejection_array():
    schema = (PROJECT_ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    analytics = (PROJECT_ROOT / "sql" / "analytics.sql").read_text(encoding="utf-8")

    for table in (
        "customers",
        "products",
        "orders",
        "order_items",
        "etl_run_log",
        "rejected_records",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
    assert "rows_duplicates INT" in schema
    assert "rejection_reasons JSON NOT NULL" in schema
    assert "JSON_TABLE(" in analytics
    assert "reasons.reason_code" in analytics
    assert "LEFT JOIN order_items" not in analytics
    assert "COALESCE(SUM(order_total), 0)" in analytics
    assert "COUNT(*) AS rejected_count" in analytics


def test_verification_sql_checks_schema_contracts():
    verification = (PROJECT_ROOT / "sql" / "verification.sql").read_text(encoding="utf-8")

    for expected in (
        "INFORMATION_SCHEMA.COLUMNS",
        "TABLE_SCHEMA = 'retail_sales_local'",
        "ORDER BY TABLE_NAME, ORDINAL_POSITION",
        "rejected_records",
        "etl_run_log",
        "COLUMN_NAME",
        "CONSTRAINT_TYPE",
        "JSON_TYPE(rejection_reasons)",
    ):
        assert expected in verification


def test_normal_pipeline_import_path_does_not_depend_on_database_loader():
    pipeline_source = (PROJECT_ROOT / "src" / "pipeline.py").read_text(encoding="utf-8")
    imported_modules = {
        alias.name
        for node in ast.walk(ast.parse(pipeline_source))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module
        for node in ast.walk(ast.parse(pipeline_source))
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert "src.load" not in imported_modules
    assert "mysql.connector" not in imported_modules
