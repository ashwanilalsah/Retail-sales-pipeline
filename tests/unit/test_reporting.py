import json

import pytest

from src.reporting import summarize_run, write_json_report


def test_summarize_run_includes_run_and_count_metadata():
    summary = summarize_run({
        "status": "success",
        "run_id": "run-1",
        "input_file": "sales.csv",
        "input_count": 5,
        "accepted_count": 3,
        "rejected_count": 2,
        "duplicate_count": 1,
    })

    assert summary["input_count"] == 5
    assert summary["accepted_count"] == 3
    assert summary["rejected_count"] == 2
    assert summary["duplicate_count"] == 1
    assert summary["run_id"] == "run-1"


def test_json_report_is_deterministic_and_refuses_overwrite(tmp_path):
    report_path = tmp_path / "reports" / "run.json"
    data = {"count": 2, "status": "success"}

    assert write_json_report(data, report_path) == str(report_path)
    original_contents = report_path.read_bytes()
    assert json.loads(original_contents) == data
    with pytest.raises(FileExistsError):
        write_json_report(data, report_path)
    assert report_path.read_bytes() == original_contents
