"""Unit tests for src/main.py orchestration."""

import json
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from main import main


def _make_envelope(subject=b"Test Subject", mailbox=b"sender", host=b"example.com"):
    envelope = MagicMock()
    envelope.subject = subject
    addr = MagicMock()
    addr.mailbox = mailbox
    addr.host = host
    envelope.from_ = [addr]
    return envelope


def _plain_email_bytes(body: str = "This is the body.") -> bytes:
    msg = EmailMessage()
    msg.set_content(body)
    return msg.as_bytes()


def test_main_processes_imap_message_and_saves(
    mock_env_vars,
    monkeypatch: pytest.MonkeyPatch,
    mock_openai_client: MagicMock,
    mock_imap_client: MagicMock,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")

    mock_imap_client.return_value.search.return_value = [1]
    mock_imap_client.return_value.list_folders.return_value = [
        (b"\\HasNoChildren", b"/", "AI-Personal")
    ]
    mock_imap_client.return_value.fetch.return_value = {
        1: {
            b"ENVELOPE": _make_envelope(),
            b"BODY[TEXT]": b"",
            b"RFC822": _plain_email_bytes(),
        }
    }

    mock_openai_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="Personal: this is personal"))
    ]

    output = tmp_path / "results.json"
    main(limit=1, save_to_json=str(output))

    mock_imap_client.return_value.copy.assert_called_once_with(1, "AI-Personal")
    mock_imap_client.return_value.delete_messages.assert_called_once_with([1])
    mock_imap_client.return_value.expunge.assert_called_once()
    mock_imap_client.return_value.logout.assert_called_once()

    data = json.loads(output.read_text())
    assert data["ai_folders"] == ["AI-Personal"]
    assert len(data["messages"]) == 1
    assert data["messages"][0]["responses"][0]["folder"] == "Personal"


def test_main_dry_run_does_not_move(
    mock_env_vars,
    monkeypatch: pytest.MonkeyPatch,
    mock_openai_client: MagicMock,
    mock_imap_client: MagicMock,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")

    mock_imap_client.return_value.search.return_value = [1]
    mock_imap_client.return_value.list_folders.return_value = [
        (b"\\HasNoChildren", b"/", "AI-Personal")
    ]
    mock_imap_client.return_value.fetch.return_value = {
        1: {
            b"ENVELOPE": _make_envelope(),
            b"BODY[TEXT]": b"",
            b"RFC822": _plain_email_bytes(),
        }
    }

    mock_openai_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="Personal: this is personal"))
    ]

    main(dry_run=True, limit=1)

    mock_imap_client.return_value.copy.assert_not_called()
    mock_imap_client.return_value.delete_messages.assert_not_called()


def test_main_accounts_processes_enabled(
    mock_env_vars: dict[str, str],
    mock_openai_client: MagicMock,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    account_file = tmp_path / "accounts.yaml"
    account_file.write_text(
        """
accounts:
  - name: personal-gmail
    provider: gmail
    username: user@gmail.com
    app_password: app-pw
    folder_prefix: AI-
    enabled: true
  - name: work
    provider: generic
    imap_host: imap.example.com
    username: user@example.com
    password: secret
    enabled: true
  - name: disabled
    provider: generic
    imap_host: imap.example.com
    username: user@example.com
    password: secret
    enabled: false
"""
    )

    mock_process = mocker.patch("main.process_account", return_value={"messages_processed": 1})

    main(accounts_file=str(account_file), limit=1)

    assert mock_process.call_count == 2
    calls = [call.args[0].name for call in mock_process.call_args_list]
    assert "personal-gmail" in calls
    assert "work" in calls
    assert mock_process.call_args.kwargs["limit"] == 1


def test_main_account_named_processes_one(
    mock_env_vars: dict[str, str],
    mock_openai_client: MagicMock,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    account_file = tmp_path / "accounts.yaml"
    account_file.write_text(
        """
accounts:
  - name: personal-gmail
    provider: gmail
    username: user@gmail.com
    app_password: app-pw
    folder_prefix: AI-
    enabled: true
  - name: work
    provider: generic
    imap_host: imap.example.com
    username: user@example.com
    password: secret
    enabled: true
"""
    )

    mock_process = mocker.patch("main.process_account", return_value={"messages_processed": 1})

    main(accounts_file=str(account_file), account_name="work")

    assert mock_process.call_count == 1
    assert mock_process.call_args[0][0].name == "work"


def test_main_accounts_missing_file_exits(
    mock_env_vars: dict[str, str],
    mock_openai_client: MagicMock,
) -> None:
    with pytest.raises(SystemExit):
        main(accounts_file="/does/not/exist.yaml")


def test_main_accounts_disabled_named_exits(
    mock_env_vars: dict[str, str],
    mock_openai_client: MagicMock,
    tmp_path: Path,
) -> None:
    account_file = tmp_path / "accounts.yaml"
    account_file.write_text(
        """
accounts:
  - name: disabled
    provider: generic
    imap_host: imap.example.com
    username: user@example.com
    password: secret
    enabled: false
"""
    )

    with pytest.raises(SystemExit):
        main(accounts_file=str(account_file), account_name="disabled")
