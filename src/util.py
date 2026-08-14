from __future__ import annotations

from colorama import Fore, Style  # type: ignore[import-untyped]
import json
import os
import re
import sys
from typing import Any

from loguru import logger

def remove_prefix(name: str, prefix: str | None = None) -> str:
    if prefix is None:
        prefix = os.environ.get("FOLDER_PREFIX", "")
    if name.startswith(prefix):
        return name[len(prefix):]
    return name

def get_stripped_folder_list(folders: list[str], prefix: str | None = None) -> list[str]:
    return [remove_prefix(folder, prefix) for folder in folders]

def limit_consecutive_linefeeds(text: str, max_linefeeds: int = 2) -> str:
    """Limit consecutive linefeeds to `max_linefeeds`."""
    pattern = r'(\n|\r\n){%d,}' % (max_linefeeds + 1)
    replacement = '\n' * max_linefeeds
    return re.sub(pattern, replacement, text)

def safe_decode(byte_content: bytes) -> str:
    try:
        return byte_content.decode('utf-8')
    except UnicodeDecodeError:
        return byte_content.decode('latin-1', errors='replace')

def save_results_to_json(ai_folders: list[str], messages: list[Any], filename: str) -> None:
    results = {
        "ai_folders": ai_folders,
        "messages": messages
    }
    with open(filename, 'w') as file:
        json.dump(results, file, indent=4)

def signal_handler(signal: int, frame: Any) -> None:
    print("\nExiting...")
    sys.exit(0)

def get_terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80

def print_line() -> None:
    print(Fore.YELLOW + "-" * get_terminal_width() + Style.RESET_ALL)


_AUDIT_LOG_FILE = os.path.expanduser("~/.sort-buddy.log")
_AUDIT_LOG_HANDLER_ID: int | None = None


def configure_audit_logger() -> None:
    """Add an idempotent loguru file sink for audit logging."""
    global _AUDIT_LOG_HANDLER_ID
    if _AUDIT_LOG_HANDLER_ID is None:
        _AUDIT_LOG_HANDLER_ID = logger.add(
            _AUDIT_LOG_FILE,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <5} | {message}",
        )
