"""Unit tests for the generic IMAP provider."""

from __future__ import annotations

from email.message import EmailMessage
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from config import EmailConfig
from email_clients.generic_imap import GenericIMAPProvider


from imapclient.exceptions import IMAPClientError


def _make_envelope(subject: bytes = b"Test Subject", mailbox: bytes = b"sender", host: bytes = b"example.com") -> MagicMock:
    envelope = MagicMock()
    envelope.subject = subject
    addr = MagicMock()
    addr.mailbox = mailbox
    addr.host = host
    envelope.from_ = [addr]
    return envelope


def _plain_email_bytes(body: str = "This is a plain text body.") -> bytes:
    msg = EmailMessage()
    msg.set_content(body)
    return msg.as_bytes()


def test_configure_sets_fields() -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    provider = GenericIMAPProvider()
    provider.configure(config)
    assert provider.host == "imap.example.com"
    assert provider.username == "u"
    assert provider.password == "p"
    assert provider.port == 993


def test_connects_and_searches(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = [1, 2]
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    provider.connect()
    mock_class.assert_called_once_with("imap.example.com", port=993, ssl=True)
    mock_class.return_value.login.assert_called_once_with("u", "p")
    mock_class.return_value.select_folder.assert_called_once_with("INBOX", readonly=False)
    assert provider.unseen_ids == [1, 2]


def test_connect_retries_on_failure(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    mock_class = mocker.MagicMock()
    mock_class.return_value.login.side_effect = [IMAPClientError("boom"), None]
    mock_class.return_value.search.return_value = [1]
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    provider.connect()
    assert mock_class.call_count == 2
    assert provider.unseen_ids == [1]


def test_connect_raises_after_exhausted_retries(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    mock_class = mocker.MagicMock()
    mock_class.return_value.login.side_effect = IMAPClientError("always fails")
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    with pytest.raises(ConnectionError):
        provider.connect()
    assert mock_class.call_count == 3


def test_list_ai_folders(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p", folder_prefix="AI-")
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = []
    mock_class.return_value.list_folders.return_value = [
        (b"\\HasNoChildren", b"/", "AI-Work"),
        (b"\\HasNoChildren", b"/", "Inbox"),
    ]
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    provider.connect()
    assert provider.list_ai_folders() == ["AI-Work"]


def test_fetch_next_message(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p", folder_prefix="AI-")
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = [1]
    envelope = _make_envelope()
    raw = _plain_email_bytes()
    mock_class.return_value.fetch.return_value = {
        1: {b"ENVELOPE": envelope, b"BODY[TEXT]": b"", b"RFC822": raw},
    }
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    provider.connect()
    msg = provider.fetch_next_message()
    assert msg is not None
    assert msg["id"] == 1
    assert msg["subject"] == "Test Subject"
    assert msg["from"] == "sender@example.com"
    assert "This is a plain text body." in msg["body"]
    mock_class.return_value.remove_flags.assert_called_once_with(1, [b"\\Seen"])
    mock_class.return_value.add_flags.assert_called_once_with(1, ["SortBuddy"])
    assert not provider.has_more_messages()


def test_dry_run_does_not_add_flag(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = []
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    provider.connect(dry_run=True)
    provider.add_flag(1, "SortBuddy")
    mock_class.return_value.add_flags.assert_not_called()


def test_move_message(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = []
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    provider.connect()
    provider.move_message(1, "AI-Work")
    mock_class.return_value.copy.assert_called_once_with(1, "AI-Work")
    mock_class.return_value.delete_messages.assert_called_once_with([1])
    mock_class.return_value.expunge.assert_called_once()


def test_close(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = []
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    provider.connect()
    provider.close()
    mock_class.return_value.logout.assert_called_once()


def test_has_flag_true(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = []
    mock_class.return_value.get_flags.return_value = {1: [b"\\Seen", b"SortBuddy"]}
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    provider.connect()
    assert provider.has_flag(1, "SortBuddy")


def test_has_flag_false(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = []
    mock_class.return_value.get_flags.return_value = {1: [b"\\Seen"]}
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    provider.connect()
    assert not provider.has_flag(1, "SortBuddy")


def test_move_message_dry_run(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = []
    provider = GenericIMAPProvider(imap_client_class=mock_class)
    provider.configure(config)
    provider.connect(dry_run=True)
    assert provider.move_message(1, "AI-Work") is True
    mock_class.return_value.copy.assert_not_called()
    mock_class.return_value.delete_messages.assert_not_called()
    mock_class.return_value.expunge.assert_not_called()
