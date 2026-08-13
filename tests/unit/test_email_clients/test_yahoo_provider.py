"""Unit tests for the Yahoo IMAP provider."""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from config import EmailConfig
from email_clients.yahoo_provider import YahooProvider


def test_configure_sets_yahoo_defaults(mocker: MockerFixture) -> None:
    config = EmailConfig(
        email_provider="yahoo",
        yahoo_username="user@yahoo.com",
        yahoo_app_password="app-pw",
        folder_prefix="AI-",
        yahoo_folder_prefix="AI-Y-",
    )
    mock_class = mocker.MagicMock()
    mock_class.return_value.search.return_value = []
    provider = YahooProvider(imap_client_class=mock_class)
    provider.configure(config)
    assert provider.host == "imap.mail.yahoo.com"
    assert provider.port == 993
    assert provider.use_ssl is True
    assert provider.username == "user@yahoo.com"
    assert provider.password == "app-pw"
    assert provider.folder_prefix == "AI-Y-"


def test_configure_missing_credentials_raises() -> None:
    config = EmailConfig(email_provider="yahoo")
    provider = YahooProvider()
    with pytest.raises(ValueError, match="Yahoo username and app password"):
        provider.configure(config)
