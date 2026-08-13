"""Unit tests for the Gmail IMAP provider."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from config import EmailConfig
from email_clients.gmail_provider import GmailProvider


def test_configure_sets_gmail_defaults(mocker: MockerFixture) -> None:
    config = EmailConfig(
        email_provider="gmail",
        gmail_username="user@gmail.com",
        gmail_app_password="app-pw",
        folder_prefix="AI-",
        gmail_label_prefix="AI-Labels-",
    )
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = []
    provider = GmailProvider(imap_client_class=mock_class)
    provider.configure(config)
    assert provider.host == "imap.gmail.com"
    assert provider.port == 993
    assert provider.use_ssl is True
    assert provider.username == "user@gmail.com"
    assert provider.password == "app-pw"
    assert provider.folder_prefix == "AI-Labels-"


def test_configure_missing_credentials_raises() -> None:
    config = EmailConfig(email_provider="gmail")
    provider = GmailProvider()
    with pytest.raises(ValueError, match="Gmail username and app password"):
        provider.configure(config)
