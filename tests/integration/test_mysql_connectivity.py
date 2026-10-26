import os

import pytest

from src.load import get_connection


_APPROVED = (
    os.getenv("DB_CONNECTION_ENABLED", "false").lower() == "true"
    and os.getenv("RUN_MYSQL_INTEGRATION") == "1"
    and os.getenv("MYSQL_INTEGRATION_APPROVAL") == "I_APPROVE_LOCAL_TEST_CONNECTION"
    and os.getenv("DB_HOST", "localhost") in {"localhost", "127.0.0.1"}
    and os.getenv("DB_NAME", "").endswith("_test")
)


@pytest.mark.skipif(
    not _APPROVED,
    reason="requires explicit approval, loopback host, and a dedicated *_test database",
)
def test_mysql_connection_handshake_only():
    connection = get_connection()
    try:
        assert connection.is_connected()
    finally:
        connection.close()
