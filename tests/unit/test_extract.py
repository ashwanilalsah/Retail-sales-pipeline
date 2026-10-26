import pandas as pd
import pytest

from src.extract import list_csv_files, read_csv_file
from src.validation import REQUIRED_COLUMNS


def test_list_csv_files_returns_sorted_csv_paths(tmp_path):
    (tmp_path / "b.csv").write_text("id\n2\n", encoding="utf-8")
    (tmp_path / "a.csv").write_text("id\n1\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    assert [path.name for path in list_csv_files(tmp_path)] == ["a.csv", "b.csv"]


def test_read_csv_file_handles_zero_byte_file(tmp_path):
    empty_file = tmp_path / "empty.csv"
    empty_file.write_bytes(b"")

    frame = read_csv_file(empty_file)

    assert frame.empty
    assert list(frame.columns) == REQUIRED_COLUMNS


def test_read_csv_file_reports_malformed_csv(tmp_path):
    malformed_file = tmp_path / "malformed.csv"
    malformed_file.write_text('left,right\n"unterminated,1\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Unable to parse CSV input"):
        read_csv_file(malformed_file)


def test_read_csv_file_reports_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        read_csv_file(tmp_path / "missing.csv")
