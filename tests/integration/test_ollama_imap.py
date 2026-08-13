"""Integration test for the Ollama + IMAP end-to-end flow."""

from __future__ import annotations

from email.message import EmailMessage
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from ai.factory import create_ai_client
from config import EmailConfig, LLMConfig
from email_clients.factory import create_email_provider


def _make_envelope(subject: bytes = b"Project update") -> MagicMock:
    envelope = MagicMock()
    envelope.subject = subject
    addr = MagicMock()
    addr.mailbox = b"boss"
    addr.host = b"example.com"
    envelope.from_ = [addr]
    return envelope


def _plain_email_bytes(body: str = "This is a work email.") -> bytes:
    msg = EmailMessage()
    msg.set_content(body)
    return msg.as_bytes()


def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the environment variables required for a mocked Ollama/IMAP run."""
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1/")
    monkeypatch.setenv("LLM_API_KEY", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:latest")
    monkeypatch.setenv("LLM_TIMEOUT", "60.0")
    monkeypatch.setenv("EMAIL_PROVIDER", "generic")
    monkeypatch.setenv("IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("IMAP_PORT", "993")
    monkeypatch.setenv("IMAP_USE_SSL", "true")
    monkeypatch.setenv("EMAIL_USERNAME", "user@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")
    monkeypatch.setenv("FOLDER_PREFIX", "AI-")


def test_ollama_imap_end_to_end(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """A full mocked end-to-end run: IMAP fetch -> Ollama classify -> IMAP move."""
    _set_test_env(monkeypatch)

    # Mock the network-facing IMAP client class.
    mock_imap_class = mocker.MagicMock()
    imap_client = mock_imap_class.return_value
    imap_client.search.return_value = [42]
    imap_client.list_folders.return_value = [
        (b"\\HasNoChildren", b"/", "AI-Work"),
    ]
    envelope = _make_envelope()
    raw = _plain_email_bytes("Please review the Q3 report.")
    imap_client.fetch.return_value = {
        42: {b"ENVELOPE": envelope, b"BODY[TEXT]": b"", b"RFC822": raw},
    }

    # Mock the OpenAI-compatible Ollama endpoint.
    mock_openai = mocker.patch("openai.OpenAI")
    raw_response = MagicMock()
    raw_response.headers = {}
    raw_response.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="AI-Work: This is a work email."))
    ]
    mock_openai.return_value.chat.completions.with_raw_response.create.return_value = raw_response

    # Build configuration from the mocked environment.
    email_config = EmailConfig()
    llm_config = LLMConfig()

    # Create and connect the email provider.
    provider = create_email_provider(
        email_config,
        dry_run=False,
        imap_client_class=mock_imap_class,
    )

    # Fetch the next unseen message.
    message = provider.fetch_next_message()
    assert message is not None
    assert message["id"] == 42
    assert message["subject"] == "Project update"

    # List AI folders on the mocked account.
    ai_folders = provider.list_ai_folders()
    assert ai_folders == ["AI-Work"]

    # Create an Ollama client from the factory and classify the email.
    ai_client = create_ai_client(llm_config)
    folder, explanation = ai_client.classify_email(message, ai_folders)
    assert folder == "AI-Work"
    assert "work" in explanation.lower()

    # Move the message into the classified folder.
    assert provider.move_message(message["id"], folder) is True
    imap_client.copy.assert_called_once_with(42, "AI-Work")
    imap_client.delete_messages.assert_called_once_with([42])
    imap_client.expunge.assert_called_once()


@pytest.mark.live
@pytest.mark.skip(reason="Requires live Ollama and IMAP services; unskip manually to run")
def test_live_ollama_imap_e2e() -> None:
    """Reserved live test for a real Ollama + IMAP end-to-end run."""
