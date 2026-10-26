from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = [
    "order_id",
    "customer_id",
    "customer_name",
    "product_id",
    "product_name",
    "category",
    "order_date",
    "quantity",
    "unit_price",
    "discount_percent",
    "total_amount",
    "payment_method",
]


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def check_missing_values(df: pd.DataFrame) -> list[str]:
    missing_columns: list[str] = []
    for column in REQUIRED_COLUMNS:
        if column in df.columns and df[column].map(_is_missing).any():
            missing_columns.append(column)
    return missing_columns


def find_duplicate_rows(df: pd.DataFrame) -> pd.Series:
    validate_required_columns(df)
    return df.duplicated(subset=list(df.columns), keep="first")


def parse_date(value: Any) -> pd.Timestamp:
    if _is_missing(value):
        raise ValueError("Date value is missing")
    try:
        parsed = pd.to_datetime(value, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid date value: {value!r}") from exc
    if pd.isna(parsed):
        raise ValueError(f"Invalid date value: {value!r}")
    return parsed


def _safe_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid_number") from exc
    if not math.isfinite(number):
        raise ValueError("invalid_number")
    return number


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _safe_quantity(value: Any) -> int:
    try:
        quantity = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("invalid_quantity") from None
    if not quantity.is_finite() or quantity != quantity.to_integral_value():
        raise ValueError("invalid_quantity")
    try:
        integer_quantity = int(quantity)
        if not math.isfinite(float(integer_quantity)):
            raise ValueError("invalid_quantity")
    except (OverflowError, ValueError):
        raise ValueError("invalid_quantity") from None
    return integer_quantity


def validate_row(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    for column in REQUIRED_COLUMNS:
        if column not in record:
            issues.append(f"missing_required_column:{column}")
        elif _is_missing(record[column]):
            issues.append(f"missing_required_value:{column}")

    quantity: int | None = None
    if "quantity" in record and not _is_blank(record["quantity"]):
        try:
            quantity = _safe_quantity(record["quantity"])
            if quantity <= 0:
                issues.append("quantity_must_be_positive")
        except ValueError:
            issues.append("invalid_quantity")

    unit_price: float | None = None
    if "unit_price" in record and not _is_blank(record["unit_price"]):
        try:
            unit_price = _safe_float(record["unit_price"])
            if unit_price <= 0:
                issues.append("unit_price_must_be_positive")
        except ValueError:
            issues.append("invalid_unit_price")

    discount_percent: float | None = None
    if "discount_percent" in record and not _is_blank(record["discount_percent"]):
        try:
            discount_percent = _safe_float(record["discount_percent"])
            if discount_percent < 0 or discount_percent > 100:
                issues.append("discount_percent_out_of_range")
        except ValueError:
            issues.append("invalid_discount_percent")

    if "order_date" in record and not _is_missing(record["order_date"]):
        try:
            parse_date(record["order_date"])
        except ValueError:
            issues.append("invalid_order_date")

    actual_total: float | None = None
    if "total_amount" in record and not _is_blank(record["total_amount"]):
        try:
            actual_total = _safe_float(record["total_amount"])
        except ValueError:
            issues.append("invalid_total_amount")

    if all(value is not None for value in (quantity, unit_price, discount_percent, actual_total)):
        expected_total = quantity * unit_price * (1 - (discount_percent / 100))
        if not math.isfinite(expected_total) or abs(actual_total - expected_total) > 0.01:
            issues.append("total_amount_mismatch")

    return issues


def validate_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    validate_required_columns(df)

    clean_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []

    for index, row in df.iterrows():
        record = row.to_dict()
        issues = validate_row(record)
        if issues:
            rejected_rows.append({"row_number": int(index), "issues": issues, "record": record})
        else:
            clean_rows.append(record)

    return pd.DataFrame(clean_rows, columns=df.columns), rejected_rows
