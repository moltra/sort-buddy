"""
Shared pytest fixtures for sort-buddy tests.

This module provides well-isolated fixtures for testing without network dependencies.
All fixtures use monkeypatch/mocker to avoid real network calls.
"""

from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """
    Fixture that sets up minimal environment variables for testing.

    Uses monkeypatch to ensure environment variables are isolated per test.
    Does not rely on real .env files.

    Returns:
        dict[str, str]: Dictionary of environment variable names and values
    """
    env_vars = {
        "LLM_PROVIDER": "openai",
        "LLM_BASE_URL": "https://api.openai.com/v1/",
        "LLM_API_KEY": "test-api-key",
        "LLM_MODEL": "gpt-4-turbo",
        "LLM_TIMEOUT": "60.0",
        "EMAIL_PROVIDER": "generic",
        "IMAP_HOST": "imap.example.com",
        "IMAP_PORT": "993",
        "IMAP_USE_SSL": "true",
        "EMAIL_USERNAME": "test@example.com",
        "EMAIL_PASSWORD": "test-password",
        "FOLDER_PREFIX": "AI-",
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def mock_openai_client(mocker: MockerFixture) -> MagicMock:
    """
    Fixture that provides a mocked OpenAI client.

    Patches the OpenAI client to avoid real API calls.
    Returns a mock object that can be configured in tests.

    Returns:
        MagicMock: Mocked OpenAI client
    """
    mock_client = mocker.patch(
        "openai.chat.completions.with_raw_response.create",
    )
    mock_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="Inbox: test response"))
    ]
    return mock_client


@pytest.fixture
def mock_imap_client(mocker: MockerFixture) -> MagicMock:
    """
    Fixture that provides a mocked IMAP client.

    Patches the IMAPClient to avoid real IMAP connections.
    Returns a mock object that can be configured in tests.

    Returns:
        MagicMock: Mocked IMAPClient
    """
    mock_imap = mocker.patch("email_fetcher.IMAPClient")
    mock_imap.return_value.search.return_value = []
    mock_imap.return_value.list_folders.return_value = []
    mock_imap.return_value.fetch.return_value = {}
    return mock_imap


@pytest.fixture
def sample_email_message() -> dict[str, str]:
    """
    Fixture that provides a sample email message for testing.

    Returns a dictionary representing a typical email structure.
    Does not include real network data.

    Returns:
        dict[str, str]: Sample email message dictionary
    """
    return {
        "id": "12345",
        "subject": "Test Email Subject",
        "from": "sender@example.com",
        "to": "recipient@example.com",
        "date": "Mon, 12 Aug 2026 10:00:00 -0000",
        "body": "This is a test email body.",
        "folder": "INBOX",
    }
