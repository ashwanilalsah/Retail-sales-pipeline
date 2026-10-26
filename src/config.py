import os
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_db_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise ValueError("DB_PORT must be an integer between 1 and 65535") from exc
    if not 1 <= port <= 65535:
        raise ValueError("DB_PORT must be an integer between 1 and 65535")
    return port


def parse_log_level(value: str) -> str:
    level = value.upper()
    if not isinstance(getattr(logging, level, None), int):
        raise ValueError("LOG_LEVEL must be a valid Python logging level")
    return level


def parse_bool(name: str, value: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false")
    return normalized == "true"


DB_HOST = get_env("DB_HOST", "localhost")
DB_PORT = parse_db_port(get_env("DB_PORT", "3306"))
DB_NAME = get_env("DB_NAME", "retail_sales_local")
DB_USER = get_env("DB_USER", "retail_user")
DB_PASSWORD = get_env("DB_PASSWORD", "change_me")
DB_CONNECT_TIMEOUT = int(get_env("DB_CONNECT_TIMEOUT", "10"))
if DB_CONNECT_TIMEOUT <= 0:
    raise ValueError("DB_CONNECT_TIMEOUT must be greater than zero")
DB_CONNECTION_ENABLED = parse_bool(
    "DB_CONNECTION_ENABLED",
    get_env("DB_CONNECTION_ENABLED", "false"),
)

INPUT_PATH = Path(get_env("INPUT_PATH", str(BASE_DIR / "data" / "raw")))
PROCESSED_PATH = Path(get_env("PROCESSED_PATH", str(BASE_DIR / "data" / "processed")))
REJECTED_PATH = Path(get_env("REJECTED_PATH", str(BASE_DIR / "data" / "rejected")))
LOG_LEVEL = parse_log_level(get_env("LOG_LEVEL", "INFO"))
LOG_FILE = os.getenv("LOG_FILE") or None
STORAGE_BACKEND = get_env("STORAGE_BACKEND", "local")
if STORAGE_BACKEND != "local":
    raise ValueError("Only STORAGE_BACKEND=local is currently supported")
AWS_REGION = get_env("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_PROFILE = os.getenv("AWS_PROFILE")


def get_db_config() -> dict[str, str | int]:
    return {
        "DB_HOST": DB_HOST,
        "DB_PORT": DB_PORT,
        "DB_NAME": DB_NAME,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "DB_CONNECT_TIMEOUT": DB_CONNECT_TIMEOUT,
        "DB_CONNECTION_ENABLED": DB_CONNECTION_ENABLED,
    }


def ensure_directories() -> None:
    for directory in (INPUT_PATH, PROCESSED_PATH, REJECTED_PATH):
        directory.mkdir(parents=True, exist_ok=True)
