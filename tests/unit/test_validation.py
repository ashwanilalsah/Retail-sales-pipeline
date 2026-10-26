import json
from pathlib import Path

import pandas as pd
import pytest

import src.pipeline as pipeline
from src.pipeline import process_csv_file
from src.validation import (
    REQUIRED_COLUMNS,
    check_missing_values,
    find_duplicate_rows,
    parse_date,
    validate_required_columns,
    validate_row,
)


def valid_record(**overrides):
    record = {
        "order_id": "A1",
        "customer_id": "C1",
        "customer_name": "Alice",
        "product_id": "P1",
        "product_name": "Keyboard",
        "category": "Electronics",
        "order_date": "2024-01-01",
        "quantity": 2,
        "unit_price": 12.50,
        "discount_percent": 10,
        "total_amount": 22.50,
        "payment_method": "Card",
    }
    return {**record, **overrides}


def write_csv(path, records):
    pd.DataFrame(records, columns=REQUIRED_COLUMNS).to_csv(path, index=False)


def configure_output_dirs(monkeypatch, tmp_path):
    processed_path = tmp_path / "processed"
    rejected_path = tmp_path / "rejected"
    monkeypatch.setattr(pipeline, "PROCESSED_PATH", processed_path)
    monkeypatch.setattr(pipeline, "REJECTED_PATH", rejected_path)
    return processed_path, rejected_path


def test_required_columns_detected():
    df = pd.DataFrame({"order_id": ["A1"], "customer_id": ["C1"]})
    with pytest.raises(ValueError):
        validate_required_columns(df)


def test_missing_values_are_detected():
    df = pd.DataFrame([
        {"order_id": "A1", "customer_id": "C1", "customer_name": None, "product_id": "P1", "product_name": "Keyboard", "category": "Electronics", "order_date": "2024-01-01", "quantity": 1, "unit_price": 12.50, "discount_percent": 0.0, "total_amount": 12.50, "payment_method": "Card"}
    ])
    issues = check_missing_values(df)
    assert "customer_name" in issues


def test_duplicate_rows_are_flagged():
    df = pd.DataFrame([
        {**valid_record(), "source_tag": "batch-a"},
        {**valid_record(), "source_tag": "batch-a"},
        {**valid_record(), "source_tag": "batch-b"},
    ])
    duplicates = find_duplicate_rows(df)
    assert duplicates.sum() == 1


def test_parse_date_accepts_valid_dates():
    parsed = parse_date("2024-02-05")
    assert parsed == pd.Timestamp("2024-02-05")


def test_validate_row_rejects_invalid_quantity():
    assert "quantity_must_be_positive" in validate_row(valid_record(quantity=0))


@pytest.mark.parametrize("quantity", [1.5, "1.25", float("inf"), float("nan"), "not-a-number"])
def test_validate_row_rejects_non_integer_or_non_finite_quantity(quantity):
    assert "invalid_quantity" in validate_row(valid_record(quantity=quantity))


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("unit_price", float("inf"), "invalid_unit_price"),
        ("unit_price", float("nan"), "invalid_unit_price"),
        ("discount_percent", float("inf"), "invalid_discount_percent"),
        ("total_amount", float("nan"), "invalid_total_amount"),
    ],
)
def test_validate_row_rejects_non_finite_numeric_values(field, value, reason):
    assert reason in validate_row(valid_record(**{field: value}))


def test_validate_row_returns_stable_missing_value_reason():
    assert "missing_required_value:customer_name" in validate_row(
        valid_record(customer_name=" ")
    )
    assert "missing_required_value:customer_name" in validate_row(
        valid_record(customer_name=float("nan"))
    )


def test_validate_row_rejects_invalid_total():
    assert "total_amount_mismatch" in validate_row(valid_record(total_amount=20.00))


def test_process_csv_file_rejects_duplicate_and_reports_consistent_counts(tmp_path, monkeypatch):
    processed_path, rejected_path = configure_output_dirs(monkeypatch, tmp_path)
    csv_path = tmp_path / "duplicates.csv"
    write_csv(csv_path, [valid_record(), valid_record(), valid_record(order_id="A2")])

    result = process_csv_file(csv_path)

    assert result["input_count"] == 3
    assert result["accepted_count"] == 2
    assert result["rejected_count"] == 1
    assert result["input_count"] == result["accepted_count"] + result["rejected_count"]
    assert Path(result["cleaned_path"]).parent == processed_path
    assert Path(result["rejected_path"]).parent == rejected_path
    assert pd.read_csv(result["cleaned_path"])["order_id"].tolist() == ["A1", "A2"]

    rejected = json.loads(Path(result["rejected_path"]).read_text(encoding="utf-8"))
    assert len(rejected) == 1
    assert rejected[0]["reason_codes"] == ["duplicate_record"]
    assert rejected[0]["record"] == valid_record()


def test_process_csv_file_handles_header_only_and_zero_byte_inputs(tmp_path, monkeypatch):
    configure_output_dirs(monkeypatch, tmp_path)
    header_only = tmp_path / "header_only.csv"
    pd.DataFrame(columns=REQUIRED_COLUMNS).to_csv(header_only, index=False)
    zero_byte = tmp_path / "zero_byte.csv"
    zero_byte.write_bytes(b"")

    for csv_path in (header_only, zero_byte):
        result = process_csv_file(csv_path)
        assert result["input_count"] == 0
        assert result["accepted_count"] == 0
        assert result["rejected_count"] == 0
        assert pd.read_csv(result["cleaned_path"]).empty
        assert json.loads(Path(result["rejected_path"]).read_text(encoding="utf-8")) == []


def test_process_csv_file_handles_all_invalid_rows(tmp_path, monkeypatch):
    configure_output_dirs(monkeypatch, tmp_path)
    csv_path = tmp_path / "invalid.csv"
    write_csv(csv_path, [valid_record(quantity=1.5), valid_record(order_id="A2", order_date="bad")])

    result = process_csv_file(csv_path)

    assert result["input_count"] == 2
    assert result["accepted_count"] == 0
    assert result["rejected_count"] == 2
    assert pd.read_csv(result["cleaned_path"]).empty
    rejected = json.loads(Path(result["rejected_path"]).read_text(encoding="utf-8"))
    assert rejected[0]["reason_codes"] == ["invalid_quantity"]
    assert rejected[1]["reason_codes"] == ["invalid_order_date"]


def test_process_csv_file_serializes_non_finite_rejected_values_as_json_strings(tmp_path, monkeypatch):
    configure_output_dirs(monkeypatch, tmp_path)
    csv_path = tmp_path / "non_finite.csv"
    write_csv(csv_path, [valid_record(unit_price=float("inf"), total_amount=float("inf"))])

    result = process_csv_file(csv_path)

    assert result["accepted_count"] == 0
    assert result["rejected_count"] == 1
    rejected = json.loads(Path(result["rejected_path"]).read_text(encoding="utf-8"))
    assert "invalid_unit_price" in rejected[0]["reason_codes"]
    assert "invalid_total_amount" in rejected[0]["reason_codes"]
    assert rejected[0]["record"]["unit_price"] == "inf"


def test_process_csv_file_outputs_are_repeatable_and_run_specific(tmp_path, monkeypatch):
    configure_output_dirs(monkeypatch, tmp_path)
    csv_path = tmp_path / "repeat.csv"
    write_csv(csv_path, [valid_record(), valid_record(), valid_record(order_id="A2", quantity=1, total_amount=12.5)])

    first = process_csv_file(csv_path)
    second = process_csv_file(csv_path)

    assert first["run_id"] != second["run_id"]
    assert first["cleaned_path"] != second["cleaned_path"]
    assert first["rejected_path"] != second["rejected_path"]
    assert Path(first["cleaned_path"]).read_bytes() == Path(second["cleaned_path"]).read_bytes()
    assert Path(first["rejected_path"]).read_bytes() == Path(second["rejected_path"]).read_bytes()


def test_process_csv_file_fails_on_collision_without_overwriting(tmp_path, monkeypatch):
    processed_path, rejected_path = configure_output_dirs(monkeypatch, tmp_path)
    csv_path = tmp_path / "collision.csv"
    write_csv(csv_path, [valid_record()])
    run_id = "fixed-run-id"
    monkeypatch.setattr(pipeline, "uuid4", lambda: type("RunId", (), {"hex": run_id})())
    processed_path.mkdir(parents=True)
    rejected_path.mkdir(parents=True)
    existing_output = processed_path / f"collision_{run_id}_cleaned.csv"
    existing_output.write_bytes(b"preserve this output")

    with pytest.raises(FileExistsError, match="Output filename collision"):
        process_csv_file(csv_path)

    assert existing_output.read_bytes() == b"preserve this output"
    assert list(rejected_path.iterdir()) == []
