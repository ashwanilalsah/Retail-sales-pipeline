from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.validation import REQUIRED_COLUMNS


def list_csv_files(directory: str | Path) -> list[Path]:
    folder = Path(directory)
    if not folder.exists():
        raise FileNotFoundError(f"Input directory does not exist: {folder}")
    files = sorted(folder.glob("*.csv"))
    return files


def read_csv_file(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    try:
        return pd.read_csv(path, keep_default_na=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ValueError(f"Unable to parse CSV input {path}: {type(exc).__name__}") from exc
