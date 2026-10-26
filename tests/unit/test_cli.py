import json

from src import cli


def test_input_files_returns_only_sorted_csvs(tmp_path):
    (tmp_path / "b.csv").write_text("id\n2\n", encoding="utf-8")
    (tmp_path / "a.csv").write_text("id\n1\n", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("ignore", encoding="utf-8")

    assert [path.name for path in cli._input_files(tmp_path)] == ["a.csv", "b.csv"]


def test_cli_prints_structured_result_without_database(monkeypatch, tmp_path, capsys):
    csv_path = tmp_path / "input.csv"
    csv_path.write_text("order_id\nO-1\n", encoding="utf-8")
    expected = {"status": "success", "input_count": 1, "accepted_count": 1, "rejected_count": 0}
    monkeypatch.setattr(cli, "process_csv_file", lambda path: expected)

    assert cli.main(["--input", str(csv_path)]) == 0
    assert json.loads(capsys.readouterr().out) == expected


def test_cli_returns_actionable_error_code_for_missing_path(tmp_path):
    missing_path = tmp_path / "missing.csv"

    assert cli.main(["--input", str(missing_path)]) == 2
