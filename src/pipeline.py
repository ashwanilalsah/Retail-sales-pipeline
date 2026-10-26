from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from src.config import LOG_FILE, LOG_LEVEL, PROCESSED_PATH, REJECTED_PATH
from src.extract import read_csv_file
from src.logging_config import configure_logging
from src.transform import normalize_record, standardize_dataframe
from src.validation import REQUIRED_COLUMNS, find_duplicate_rows, validate_required_columns, validate_row


def build_run_log(run_id: str, source_file: str, stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "source_file": source_file,
        "status": stats.get("status", "success"),
        "input_count": stats.get("input_count", stats.get("rows_read", 0)),
        "accepted_count": stats.get("accepted_count", stats.get("rows_valid", 0)),
        "rejected_count": stats.get("rejected_count", stats.get("rows_rejected", 0)),
        "duplicate_count": stats.get("duplicate_count", 0),
        "rows_read": stats.get("rows_read", 0),
        "rows_valid": stats.get("rows_valid", 0),
        "rows_rejected": stats.get("rows_rejected", 0),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    return value


def process_csv_file(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    run_id = uuid4().hex
    logger = configure_logging(LOG_FILE, getattr(logging, LOG_LEVEL))
    logger.info("etl_run_started source_file=%s", path.name)

    try:
        df = read_csv_file(path)
        validate_required_columns(df)
        duplicate_mask = find_duplicate_rows(df)

        valid_rows: list[dict[str, Any]] = []
        rejected_rows: list[dict[str, Any]] = []

        for index, row in df.iterrows():
            record = row.to_dict()
            if duplicate_mask.iloc[index]:
                rejected_rows.append({
                    "row_number": int(index),
                    "reason_codes": ["duplicate_record"],
                    "record": record,
                })
                continue

            issues = validate_row(record)
            if issues:
                rejected_rows.append({
                    "row_number": int(index),
                    "reason_codes": issues,
                    "record": record,
                })
                continue
            normalized = normalize_record(record)
            valid_rows.append(normalized)

        columns = list(df.columns) if len(df.columns) else REQUIRED_COLUMNS
        valid_df = pd.DataFrame(valid_rows, columns=columns)
        cleaned_df = standardize_dataframe(valid_df) if valid_rows else pd.DataFrame(columns=columns)
        cleaned_contents = cleaned_df.to_csv(index=False, lineterminator="\n")
        rejected_contents = json.dumps(
            _json_safe(rejected_rows),
            ensure_ascii=False,
            indent=2,
            default=str,
            allow_nan=False,
        ) + "\n"

        PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
        REJECTED_PATH.mkdir(parents=True, exist_ok=True)
        cleaned_path = PROCESSED_PATH / f"{path.stem}_{run_id}_cleaned.csv"
        rejected_path = REJECTED_PATH / f"{path.stem}_{run_id}_rejected.json"
        output_contents = (
            (cleaned_path, cleaned_contents),
            (rejected_path, rejected_contents),
        )

        collisions = [output_path for output_path, _ in output_contents if output_path.exists()]
        if collisions:
            collision_list = ", ".join(str(output_path) for output_path in collisions)
            raise FileExistsError(f"Output filename collision: {collision_list}")

        created_paths: list[Path] = []
        try:
            for output_path, contents in output_contents:
                with output_path.open("x", encoding="utf-8", newline="") as output_file:
                    created_paths.append(output_path)
                    output_file.write(contents)
        except FileExistsError as exc:
            for created_path in created_paths:
                created_path.unlink(missing_ok=True)
            raise FileExistsError(f"Output filename collision while creating: {exc.filename}") from exc
        except Exception:
            for created_path in created_paths:
                created_path.unlink(missing_ok=True)
            raise

        result = {
            "status": "success",
            "run_id": run_id,
            "input_file": str(path),
            "input_count": len(df),
            "accepted_count": len(valid_rows),
            "rejected_count": len(rejected_rows),
            "duplicate_count": int(duplicate_mask.sum()),
            "rows_read": len(df),
            "rows_valid": len(valid_rows),
            "rows_rejected": len(rejected_rows),
            "cleaned_path": str(cleaned_path),
            "rejected_path": str(rejected_path),
        }
        logger.info(
            "etl_run_completed input_count=%d accepted_count=%d rejected_count=%d duplicate_count=%d",
            result["input_count"],
            result["accepted_count"],
            result["rejected_count"],
            result["duplicate_count"],
        )
        return result
    except Exception as exc:
        logger.error("etl_run_failed error_type=%s", type(exc).__name__)
        raise
