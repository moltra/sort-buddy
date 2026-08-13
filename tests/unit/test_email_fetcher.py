"""Unit tests for src/email_fetcher.py."""

from email.message import EmailMessage
from unittest.mock import MagicMock

import pytest

from email_fetcher import EmailFetcher


@pytest.fixture
def make_envelope():
    """Factory for a mock IMAP envelope."""
    def _make(subject=b"Test Subject", mailbox=b"sender", host=b"example.com"):
        envelope = MagicMock()
        envelope.subject = subject
        addr = MagicMock()
        addr.mailbox = mailbox
        addr.host = host
        envelope.from_ = [addr]
        return envelope
    return _make


def _plain_email_bytes(body: str = "This is a plain text body.") -> bytes:
    msg = EmailMessage()
    msg.set_content(body)
    return msg.as_bytes()


def _multipart_email_bytes() -> bytes:
    msg = EmailMessage()
    msg.set_content("plain text part")
    msg.add_alternative("<html><body>html part</body></html>", subtype="html")
    return msg.as_bytes()


def test_init_connects_and_searches(
    mock_env_vars, mock_imap_client: MagicMock
) -> None:
    mock_imap_client.return_value.search.return_value = [1]
    fetcher = EmailFetcher()
    mock_imap_client.assert_called_once_with("imap.example.com", ssl=True)
    mock_imap_client.return_value.login.assert_called_once_with(
        "test@example.com", "test-password"
    )
    mock_imap_client.return_value.select_folder.assert_called_once_with(
        "INBOX", readonly=False
    )
    mock_imap_client.return_value.search.assert_called_once_with(
        ["UNSEEN", "NOT", "KEYWORD", "SortBuddy"]
    )
    assert fetcher.unseen_ids == [1]


def test_list_ai_folders(mock_env_vars, mock_imap_client: MagicMock) -> None:
    mock_imap_client.return_value.search.return_value = []
    mock_imap_client.return_value.list_folders.return_value = [
        (b"\\HasNoChildren", b"/", "AI-Work"),
        (b"\\HasNoChildren", b"/", "Inbox"),
    ]
    fetcher = EmailFetcher()
    assert fetcher.list_ai_folders() == ["AI-Work"]


def test_fetch_next_message_plain_text(
    mock_env_vars, mock_imap_client: MagicMock, make_envelope
) -> None:
    mock_imap_client.return_value.search.return_value = [1]
    envelope = make_envelope()
    raw = _plain_email_bytes()
    mock_imap_client.return_value.fetch.return_value = {
        1: {
            b"ENVELOPE": envelope,
            b"BODY[TEXT]": b"",
            b"RFC822": raw,
        }
    }
    fetcher = EmailFetcher()
    msg = fetcher.fetch_next_message()
    assert msg is not None
    assert msg["id"] == 1
    assert msg["subject"] == "Test Subject"
    assert "sender@example.com" == msg["from"]
    assert "This is a plain text body." in msg["body"]
    mock_imap_client.return_value.remove_flags.assert_called_once_with(1, [b"\\Seen"])
    mock_imap_client.return_value.add_flags.assert_called_once_with(1, ["SortBuddy"])
    assert not fetcher.has_more_messages()


def test_fetch_next_message_multipart(
    mock_env_vars, mock_imap_client: MagicMock, make_envelope
) -> None:
    mock_imap_client.return_value.search.return_value = [1]
    envelope = make_envelope()
    raw = _multipart_email_bytes()
    mock_imap_client.return_value.fetch.return_value = {
        1: {
            b"ENVELOPE": envelope,
            b"BODY[TEXT]": b"",
            b"RFC822": raw,
        }
    }
    fetcher = EmailFetcher()
    msg = fetcher.fetch_next_message()
    assert msg is not None
    assert "plain text part" in msg["body"]
    assert "html part" in msg["body"]


def test_fetch_next_message_returns_none_when_empty(
    mock_env_vars, mock_imap_client: MagicMock
) -> None:
    mock_imap_client.return_value.search.return_value = []
    fetcher = EmailFetcher()
    assert fetcher.fetch_next_message() is None


def test_has_more_messages(mock_env_vars, mock_imap_client: MagicMock) -> None:
    mock_imap_client.return_value.search.return_value = [1, 2]
    fetcher = EmailFetcher()
    assert fetcher.has_more_messages()
    fetcher.current_index = 2
    assert not fetcher.has_more_messages()


def test_add_flag_noop_when_dry_run(mock_env_vars, mock_imap_client: MagicMock) -> None:
    mock_imap_client.return_value.search.return_value = []
    fetcher = EmailFetcher(dry_run=True)
    fetcher.add_flag(1, "SortBuddy")
    mock_imap_client.return_value.add_flags.assert_not_called()


def test_has_flag(mock_env_vars, mock_imap_client: MagicMock) -> None:
    mock_imap_client.return_value.search.return_value = []
    mock_imap_client.return_value.get_flags.return_value = [b"\\Seen", "SortBuddy"]
    fetcher = EmailFetcher()
    assert fetcher.has_flag(1, "SortBuddy")
    assert not fetcher.has_flag(1, "Missing")


def test_move_message(mock_env_vars, mock_imap_client: MagicMock) -> None:
    mock_imap_client.return_value.search.return_value = []
    fetcher = EmailFetcher()
    fetcher.move_message(1, "AI-Work")
    mock_imap_client.return_value.copy.assert_called_once_with(1, "AI-Work")
    mock_imap_client.return_value.delete_messages.assert_called_once_with([1])
    mock_imap_client.return_value.expunge.assert_called_once()


def test_move_message_swallows_exception(
    mock_env_vars, mock_imap_client: MagicMock, capsys
) -> None:
    mock_imap_client.return_value.search.return_value = []
    mock_imap_client.return_value.copy.side_effect = Exception("IMAP failure")
    fetcher = EmailFetcher()
    fetcher.move_message(1, "AI-Work")
    captured = capsys.readouterr()
    assert "IMAP failure" in captured.out


def test_close(mock_env_vars, mock_imap_client: MagicMock) -> None:
    mock_imap_client.return_value.search.return_value = []
    fetcher = EmailFetcher()
    fetcher.close()
    mock_imap_client.return_value.logout.assert_called_once()
