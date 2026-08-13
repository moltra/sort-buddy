"""Unit tests for src/util.py."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import util


@pytest.fixture
def set_folder_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set FOLDER_PREFIX for prefix removal tests."""
    monkeypatch.setenv("FOLDER_PREFIX", "AI-")


def test_remove_prefix_strips_match(set_folder_prefix: None) -> None:
    assert util.remove_prefix("AI-Work") == "Work"


def test_remove_prefix_ignores_non_match(set_folder_prefix: None) -> None:
    assert util.remove_prefix("Inbox") == "Inbox"


def test_get_stripped_folder_list(set_folder_prefix: None) -> None:
    folders = ["AI-Work", "AI-Personal", "Inbox"]
    assert util.get_stripped_folder_list(folders) == ["Work", "Personal", "Inbox"]


def test_limit_consecutive_linefeeds() -> None:
    text = "line1\n\n\n\nline2"
    assert util.limit_consecutive_linefeeds(text, 2) == "line1\n\nline2"


def test_limit_consecutive_linefeeds_crlf() -> None:
    text = "line1\r\n\r\n\r\n\r\nline2"
    # The helper normalizes CRLF runs down to LF runs.
    assert util.limit_consecutive_linefeeds(text, 2) == "line1\n\nline2"


def test_safe_decode_utf8() -> None:
    assert util.safe_decode(b"hello") == "hello"


def test_safe_decode_falls_back_to_latin1() -> None:
    # Invalid utf-8 bytes that latin-1 can interpret
    assert util.safe_decode(b"\xff\xfe") == "\xff\xfe"


def test_save_results_to_json(tmp_path: Path) -> None:
    filename = tmp_path / "results.json"
    util.save_results_to_json(["AI-Work"], [{"id": 1}], str(filename))
    data = json.loads(filename.read_text())
    assert data == {"ai_folders": ["AI-Work"], "messages": [{"id": 1}]}


def test_get_terminal_width_os_error() -> None:
    with patch("os.get_terminal_size", side_effect=OSError):
        assert util.get_terminal_width() == 80


def test_print_line(capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOLDER_PREFIX", "AI-")
    with patch("util.get_terminal_width", return_value=10):
        util.print_line()
    captured = capsys.readouterr()
    assert "-" in captured.out
