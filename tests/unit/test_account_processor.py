"""Unit tests for src/account_processor.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from pytest_mock import MockerFixture

from account_processor import process_account
from accounts_config import AccountConfig


def _account_config(provider: str = "generic") -> AccountConfig:
    if provider == "generic":
        return AccountConfig(
            name="work",
            provider="generic",
            imap_host="imap.example.com",
            username="user@example.com",
            password="secret",
            folder_prefix="AI-",
        )
    if provider == "gmail":
        return AccountConfig(
            name="gmail",
            provider="gmail",
            username="user@gmail.com",
            app_password="gmail-app-pw",
            folder_prefix="AI-",
        )
    return AccountConfig(
        name="yahoo",
        provider="yahoo",
        username="user@yahoo.com",
        app_password="yahoo-app-pw",
        folder_prefix="AI-",
    )


def _make_fetcher(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("account_processor.EmailFetcher")
    instance = mock.return_value
    instance.list_ai_folders.return_value = ["AI-Work", "AI-Personal"]
    instance.has_more_messages.side_effect = [True, True, False]
    instance.fetch_next_message.side_effect = [
        {
            "id": 1,
            "from": "sender1@example.com",
            "subject": "First",
            "body": "body one",
            "responses": [],
        },
        {
            "id": 2,
            "from": "sender2@example.com",
            "subject": "Second",
            "body": "body two",
            "responses": [],
        },
        None,
    ]
    return mock


def test_process_account_success(
    mock_env_vars: dict[str, str],
    mocker: MockerFixture,
) -> None:
    _make_fetcher(mocker)
    mocker.patch("account_processor.get_ai_response_from_message", return_value=("Work", "explanation"))

    stats = process_account(_account_config(), dry_run=False)

    assert stats["account_name"] == "work"
    assert stats["messages_processed"] == 2
    assert stats["errors"] == 0


def test_process_account_honors_limit(
    mock_env_vars: dict[str, str],
    mocker: MockerFixture,
) -> None:
    _make_fetcher(mocker)
    mocker.patch("account_processor.get_ai_response_from_message", return_value=("Work", "explanation"))

    stats = process_account(_account_config(), dry_run=False, limit=1)

    assert stats["messages_processed"] == 1


def test_process_account_dry_run_does_not_move(
    mock_env_vars: dict[str, str],
    mocker: MockerFixture,
) -> None:
    fetcher_mock = _make_fetcher(mocker)
    mocker.patch("account_processor.get_ai_response_from_message", return_value=("Work", "explanation"))

    process_account(_account_config(), dry_run=True)

    fetcher_mock.return_value.move_message.assert_not_called()


def test_process_account_counts_ai_errors(
    mock_env_vars: dict[str, str],
    mocker: MockerFixture,
) -> None:
    _make_fetcher(mocker)
    mocker.patch("account_processor.get_ai_response_from_message", side_effect=Exception("AI error"))

    stats = process_account(_account_config(), dry_run=False)

    assert stats["messages_processed"] == 0
    assert stats["errors"] == 2


def test_process_account_saves_to_json(
    mock_env_vars: dict[str, str],
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    _make_fetcher(mocker)
    mocker.patch("account_processor.get_ai_response_from_message", return_value=("Work", "explanation"))

    output_base = str(tmp_path / "results")
    stats = process_account(_account_config(), dry_run=True, save_to_json=output_base)

    output_path = f"{output_base}-work.json"
    assert Path(output_path).exists()
    data = json.loads(Path(output_path).read_text())
    assert data["ai_folders"] == ["AI-Work", "AI-Personal"]
    assert len(data["messages"]) == 2
    assert stats["ai_folders"] == data["ai_folders"]


def test_process_account_gmail(
    mock_env_vars: dict[str, str],
    mocker: MockerFixture,
) -> None:
    _make_fetcher(mocker)
    mocker.patch("account_processor.get_ai_response_from_message", return_value=("Work", "explanation"))

    stats = process_account(_account_config("gmail"), dry_run=True)

    assert stats["account_name"] == "gmail"
    assert stats["messages_processed"] == 2


def test_process_account_yahoo(
    mock_env_vars: dict[str, str],
    mocker: MockerFixture,
) -> None:
    _make_fetcher(mocker)
    mocker.patch("account_processor.get_ai_response_from_message", return_value=("Work", "explanation"))

    stats = process_account(_account_config("yahoo"), dry_run=True)

    assert stats["account_name"] == "yahoo"
    assert stats["messages_processed"] == 2


def test_process_account_uses_account_folder_prefix(
    mock_env_vars: dict[str, str],
    mocker: MockerFixture,
) -> None:
    fetcher_mock = _make_fetcher(mocker)
    fetcher_mock.return_value.list_ai_folders.return_value = ["Custom-Work", "Custom-Personal"]
    mocker.patch("account_processor.get_ai_response_from_message", return_value=("Work", "explanation"))

    account = _account_config()
    account.folder_prefix = "Custom-"
    process_account(account, dry_run=False)

    fetcher_mock.return_value.move_message.assert_has_calls(
        [call(1, "Custom-Work"), call(2, "Custom-Work")], any_order=True
    )
