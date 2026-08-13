"""Unit tests for the email provider factory."""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from config import EmailConfig
from email_clients.factory import create_email_provider
from email_clients.generic_imap import GenericIMAPProvider
from email_clients.gmail_provider import GmailProvider
from email_clients.yahoo_provider import YahooProvider


def _mock_imap_class(mocker: MockerFixture) -> None:
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = []
    return mock_class


def test_factory_creates_generic(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="generic", imap_host="imap.example.com", email_username="u", email_password="p")
    mock_class = _mock_imap_class(mocker)
    provider = create_email_provider(config, dry_run=True, imap_client_class=mock_class)
    assert isinstance(provider, GenericIMAPProvider)
    mock_class.assert_called_once_with("imap.example.com", port=993, ssl=True)


def test_factory_creates_gmail(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="gmail", gmail_username="u", gmail_app_password="p")
    mock_class = _mock_imap_class(mocker)
    provider = create_email_provider(config, dry_run=True, imap_client_class=mock_class)
    assert isinstance(provider, GmailProvider)
    mock_class.assert_called_once_with("imap.gmail.com", port=993, ssl=True)


def test_factory_creates_yahoo(mocker: MockerFixture) -> None:
    config = EmailConfig(email_provider="yahoo", yahoo_username="u", yahoo_app_password="p")
    mock_class = _mock_imap_class(mocker)
    provider = create_email_provider(config, dry_run=True, imap_client_class=mock_class)
    assert isinstance(provider, YahooProvider)
    mock_class.assert_called_once_with("imap.mail.yahoo.com", port=993, ssl=True)


def test_factory_rejects_unknown_provider() -> None:
    config = EmailConfig(email_provider="outlook")
    with pytest.raises(ValueError, match="Unknown email provider"):
        create_email_provider(config)
