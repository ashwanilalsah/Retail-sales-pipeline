from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from src.validation import REQUIRED_COLUMNS, validate_required_columns


def standardize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    validate_required_columns(df)
    cleaned = df.copy()

    for column in REQUIRED_COLUMNS:
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].map(
                lambda value: (value.strip() or None)
                if isinstance(value, str)
                else (None if pd.isna(value) else value)
            )

    cleaned["quantity"] = pd.to_numeric(cleaned["quantity"], errors="coerce")
    cleaned["unit_price"] = pd.to_numeric(cleaned["unit_price"], errors="coerce")
    cleaned["discount_percent"] = pd.to_numeric(cleaned["discount_percent"], errors="coerce")
    cleaned["total_amount"] = pd.to_numeric(cleaned["total_amount"], errors="coerce")
    cleaned["order_date"] = pd.to_datetime(cleaned["order_date"], errors="coerce")
    cleaned["customer_name"] = cleaned["customer_name"].fillna("Unknown")
    cleaned["product_name"] = cleaned["product_name"].fillna("Unknown")
    cleaned["category"] = cleaned["category"].fillna("Uncategorized")

    return cleaned


def compute_line_total(row: dict[str, Any]) -> float:
    quantity = float(row.get("quantity", 0) or 0)
    unit_price = float(row.get("unit_price", 0) or 0)
    discount_percent = float(row.get("discount_percent", 0) or 0)
    return quantity * unit_price * (1 - (discount_percent / 100))


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    if "quantity" in normalized and normalized["quantity"] is not None:
        try:
            quantity = Decimal(str(normalized["quantity"]))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("quantity must be a whole number") from exc
        if not quantity.is_finite() or quantity != quantity.to_integral_value():
            raise ValueError("quantity must be a whole number")
        normalized["quantity"] = int(quantity)
    if "unit_price" in normalized and normalized["unit_price"] is not None:
        normalized["unit_price"] = float(normalized["unit_price"])
    if "discount_percent" in normalized and normalized["discount_percent"] is not None:
        normalized["discount_percent"] = float(normalized["discount_percent"])
    if "total_amount" in normalized and normalized["total_amount"] is not None:
        normalized["total_amount"] = float(normalized["total_amount"])
    if "order_date" in normalized and normalized["order_date"] is not None:
        normalized["order_date"] = pd.to_datetime(normalized["order_date"]).strftime("%Y-%m-%d")
    return normalized
