from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def utc_file_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(path: Path, payload: object) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
