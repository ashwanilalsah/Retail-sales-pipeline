from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from src.config import INPUT_PATH, LOG_FILE, LOG_LEVEL
from src.extract import list_csv_files
from src.logging_config import configure_logging
from src.pipeline import process_csv_file


def _input_files(input_path: Path) -> list[Path]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")
    if input_path.is_file():
        if input_path.suffix.lower() != ".csv":
            raise ValueError(f"Input file must have a .csv extension: {input_path}")
        return [input_path]
    return list_csv_files(input_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Retail Sales CSV ETL pipeline.")
    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_PATH,
        help="CSV input file or directory (default: INPUT_PATH)",
    )
    args = parser.parse_args(argv)
    logger = configure_logging(LOG_FILE, getattr(logging, LOG_LEVEL))

    try:
        files = _input_files(args.input)
        if not files:
            logger.warning("no_csv_inputs input_path=%s", args.input)
            return 0
        for file_path in files:
            result = process_csv_file(file_path)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except (FileNotFoundError, ValueError, OSError) as exc:
        logger.error("cli_run_failed error_type=%s message=%s", type(exc).__name__, str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
