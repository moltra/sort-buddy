"""Unit tests for src/main.py orchestration."""

import json
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import MagicMock

import pytest

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
        (b"\\HasNoChildren", b"/", "AI-Work")
    ]
    mock_imap_client.return_value.fetch.return_value = {
        1: {
            b"ENVELOPE": _make_envelope(),
            b"BODY[TEXT]": b"",
            b"RFC822": _plain_email_bytes(),
        }
    }

    mock_openai_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="Work: this is work"))
    ]

    output = tmp_path / "results.json"
    main(limit=1, save_to_json=str(output))

    mock_imap_client.return_value.copy.assert_called_once_with(1, "AI-Work")
    mock_imap_client.return_value.delete_messages.assert_called_once_with([1])
    mock_imap_client.return_value.expunge.assert_called_once()
    mock_imap_client.return_value.logout.assert_called_once()

    data = json.loads(output.read_text())
    assert data["ai_folders"] == ["AI-Work"]
    assert len(data["messages"]) == 1
    assert data["messages"][0]["responses"][0]["folder"] == "Work"


def test_main_dry_run_does_not_move(
    mock_env_vars,
    monkeypatch: pytest.MonkeyPatch,
    mock_openai_client: MagicMock,
    mock_imap_client: MagicMock,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")

    mock_imap_client.return_value.search.return_value = [1]
    mock_imap_client.return_value.list_folders.return_value = [
        (b"\\HasNoChildren", b"/", "AI-Work")
    ]
    mock_imap_client.return_value.fetch.return_value = {
        1: {
            b"ENVELOPE": _make_envelope(),
            b"BODY[TEXT]": b"",
            b"RFC822": _plain_email_bytes(),
        }
    }

    mock_openai_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="Work: this is work"))
    ]

    main(dry_run=True, limit=1)

    mock_imap_client.return_value.copy.assert_not_called()
    mock_imap_client.return_value.delete_messages.assert_not_called()
