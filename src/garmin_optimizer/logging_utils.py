from __future__ import annotations

import logging
from pathlib import Path

from garmin_optimizer.services.redaction import RedactionService


class RedactionFilter(logging.Filter):
    def __init__(self, redactor: RedactionService) -> None:
        super().__init__()
        self.redactor = redactor

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.redactor.redact_text(record.getMessage())
        record.args = ()
        return True


def setup_logging(logs_dir: Path, redactor: RedactionService, level: int = logging.INFO) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "garmin_optimizer.log"
    logger = logging.getLogger("garmin_optimizer")
    if logger.handlers:
        return

    logger.setLevel(level)
    logger.propagate = False
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    redaction_filter = RedactionFilter(redactor)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redaction_filter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(redaction_filter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
