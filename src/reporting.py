from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_report(data: dict[str, Any], output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        default=str,
        allow_nan=False,
    ) + "\n"
    with path.open("x", encoding="utf-8", newline="") as report_file:
        report_file.write(contents)
    return str(path)


def summarize_run(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": result.get("status", "success"),
        "run_id": result.get("run_id"),
        "input_file": result.get("input_file"),
        "input_count": result.get("input_count", result.get("rows_read", 0)),
        "accepted_count": result.get("accepted_count", result.get("rows_valid", 0)),
        "rejected_count": result.get("rejected_count", result.get("rows_rejected", 0)),
        "duplicate_count": result.get("duplicate_count", 0),
        "rows_read": result.get("rows_read", 0),
        "rows_valid": result.get("rows_valid", 0),
        "rows_rejected": result.get("rows_rejected", 0),
        "cleaned_path": result.get("cleaned_path"),
        "rejected_path": result.get("rejected_path"),
    }
