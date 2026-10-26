
import logging
import json
from pathlib import Path
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(
    log_file: str | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger("retail_sales_pipeline")
    logger.setLevel(level)
    logger.propagate = False

    formatter = _JsonFormatter()

    stream_handlers = [
        h for h in logger.handlers
        if getattr(h, "_retail_stream_handler", False)
    ]

    if stream_handlers:
        stream_handler = stream_handlers[0]
        for extra in stream_handlers[1:]:
            logger.removeHandler(extra)
            extra.close()
    else:
        stream_handler = logging.StreamHandler()
        stream_handler._retail_stream_handler = True
        logger.addHandler(stream_handler)

    stream_handler.setFormatter(formatter)

    if log_file:
        log_path = Path(log_file).resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        matching_handler = None

        for handler in list(logger.handlers):
            if isinstance(handler, logging.FileHandler):
                if (
                    Path(handler.baseFilename).resolve() == log_path
                    and matching_handler is None
                ):
                    matching_handler = handler
                else:
                    logger.removeHandler(handler)
                    handler.close()

        if matching_handler is None:
            matching_handler = logging.FileHandler(
                log_path, encoding="utf-8"
            )
            logger.addHandler(matching_handler)

        matching_handler.setFormatter(formatter)

    return logger
