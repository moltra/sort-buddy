"""History and feedback logging for sort-buddy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HISTORY_PATH = Path.home() / ".sort-buddy-history.jsonl"
FEEDBACK_PATH = Path.home() / ".sort-buddy-feedback.jsonl"


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_history(record: dict[str, Any]) -> None:
    """Append a record to the classification history log."""
    _append_jsonl(HISTORY_PATH, record)


def append_feedback(record: dict[str, Any]) -> None:
    """Append a record to the feedback log."""
    _append_jsonl(FEEDBACK_PATH, record)
