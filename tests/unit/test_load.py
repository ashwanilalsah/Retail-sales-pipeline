import json
from datetime import date
from decimal import Decimal

import pytest

from src import load


class FakeCursor:
    def __init__(self, fail_on=None):
        self.executions = []
        self.fail_on = fail_on
        self.closed = False
        self.rowcount = 1

    def execute(self, statement, params=None):
        self.executions.append((statement, params))
        if self.fail_on and self.fail_on in statement:
            raise RuntimeError("mock database failure with password=should-not-log")

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, fail_on=None):
        self.fake_cursor = FakeCursor(fail_on)
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def accepted_record():
    return {
        "order_id": "O-1",
        "customer_id": "C-1",
        "customer_name": "Ada",
        "product_id": "P-1",
        "product_name": "Keyboard",
        "category": "Electronics",
        "order_date": "2024-03-02",
        "quantity": 2,
        "unit_price": 10.0,
        "discount_percent": 0.0,
        "total_amount": 20.0,
        "payment_method": "Card",
    }


def run_metadata(accepted=1, rejected=1):
    return {
        "run_id": "run-1",
        "input_file": "sample.csv",
        "input_count": accepted + rejected,
        "accepted_count": accepted,
        "rejected_count": rejected,
        "duplicate_count": 0,
    }


def rejected_record():
    return {
        "row_number": 1,
        "reason_codes": ["invalid_order_date"],
        "record": {"order_id": "O-2", "order_date": "bad"},
    }


def test_load_run_result_uses_parameterized_sql_and_commits_once():
    connection = FakeConnection()

    result = load.load_run_result(
        connection,
        run_metadata(),
        [accepted_record()],
        [rejected_record()],
    )

    assert result["status"] == "success"
    assert result["input_count"] == 2
    assert result["accepted_count"] == 1
    assert result["rejected_count"] == 1
    assert result["orders_loaded"] == 1
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.fake_cursor.closed
    assert all("%s" in statement for statement, _ in connection.fake_cursor.executions)
    statement_text = [statement for statement, _ in connection.fake_cursor.executions]
    assert "ON DUPLICATE KEY UPDATE" in statement_text[0]
    assert next(i for i, statement in enumerate(statement_text) if "INSERT INTO orders" in statement) < next(
        i for i, statement in enumerate(statement_text) if "INSERT INTO order_items" in statement
    )
    rejected_statement = next(
        statement for statement in statement_text if "INSERT INTO rejected_records" in statement
    )
    assert "ON DUPLICATE KEY UPDATE" in rejected_statement

    order_insert = next(
        params for statement, params in connection.fake_cursor.executions
        if "INSERT INTO orders" in statement
    )
    assert order_insert == ("O-1", "C-1", date(2024, 3, 2), "Card", Decimal("20.0"))

    rejected_insert = next(
        params for statement, params in connection.fake_cursor.executions
        if "INSERT INTO rejected_records" in statement
    )
    assert json.loads(rejected_insert[3]) == rejected_record()["record"]
    assert json.loads(rejected_insert[4]) == ["invalid_order_date"]


def test_load_run_result_rolls_back_and_does_not_log_error_details(caplog):
    connection = FakeConnection(fail_on="INSERT INTO products")

    with pytest.raises(RuntimeError, match="mock database failure"):
        load.load_run_result(connection, run_metadata(rejected=0), [accepted_record()])

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.fake_cursor.closed
    assert "should-not-log" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_load_run_result_rejects_inconsistent_counts_before_cursor_use():
    connection = FakeConnection()
    metadata = run_metadata(accepted=2, rejected=0)

    with pytest.raises(ValueError, match="counts do not match"):
        load.load_run_result(connection, metadata, [accepted_record()], [])

    assert connection.fake_cursor.executions == []
    assert connection.commits == 0
    assert connection.rollbacks == 0


def test_get_connection_forwards_settings_to_connector(monkeypatch):
    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(load.mysql.connector, "connect", fake_connect)
    load.get_connection({
        "DB_HOST": "db.example.test",
        "DB_PORT": 3307,
        "DB_NAME": "retail_test",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "DB_CONNECT_TIMEOUT": 5,
        "DB_CONNECTION_ENABLED": True,
    })

    assert captured == {
        "host": "db.example.test",
        "port": 3307,
        "user": "test_user",
        "password": "test_password",
        "database": "retail_test",
        "autocommit": False,
        "connection_timeout": 5,
    }


def test_get_connection_is_disabled_without_explicit_opt_in(monkeypatch):
    def unexpected_connect(**kwargs):
        raise AssertionError("connector must not be called while DB connections are disabled")

    monkeypatch.setattr(load.mysql.connector, "connect", unexpected_connect)
    with pytest.raises(RuntimeError, match="DB_CONNECTION_ENABLED=true"):
        load.get_connection({
            "DB_HOST": "localhost",
            "DB_PORT": 3306,
            "DB_NAME": "retail_sales_local",
            "DB_USER": "retail_user",
            "DB_PASSWORD": "unused",
        })


def test_load_run_outputs_closes_owned_connection(tmp_path, monkeypatch):
    cleaned_path = tmp_path / "cleaned.csv"
    cleaned_path.write_text(
        "order_id,customer_id,customer_name,product_id,product_name,category,order_date,quantity,unit_price,discount_percent,total_amount,payment_method\n"
        "O-1,C-1,Ada,P-1,Keyboard,Electronics,2024-03-02,2,10,0,20,Card\n",
        encoding="utf-8",
    )
    rejected_path = tmp_path / "rejected.json"
    rejected_path.write_text("[]\n", encoding="utf-8")
    connection = FakeConnection()
    monkeypatch.setattr(load, "get_connection", lambda config=None: connection)
    metadata = {
        **run_metadata(rejected=0),
        "cleaned_path": str(cleaned_path),
        "rejected_path": str(rejected_path),
    }

    result = load.load_run_outputs(metadata, {"unused": True})

    assert result["accepted_count"] == 1
    assert connection.commits == 1
    assert connection.closed
