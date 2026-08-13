"""Comprehensive unit tests for src/config.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from config import EmailConfig, LLMConfig

_LLM_ENV_KEYS = [
    "LLM_PROVIDER",
    "LLM_BASE_URL",
    "LLM_API_KEY",
    "LLM_MODEL",
    "LLM_TIMEOUT",
    "OPENAI_API_KEY",
    "OPENAI_API_URL",
    "OPENAI_MODEL",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_TIMEOUT",
]

_EMAIL_ENV_KEYS = [
    "EMAIL_PROVIDER",
    "IMAP_HOST",
    "IMAP_PORT",
    "IMAP_USE_SSL",
    "EMAIL_USERNAME",
    "EMAIL_PASSWORD",
    "FOLDER_PREFIX",
    "GMAIL_USERNAME",
    "GMAIL_APP_PASSWORD",
    "GMAIL_LABEL_PREFIX",
    "YAHOO_USERNAME",
    "YAHOO_APP_PASSWORD",
    "YAHOO_FOLDER_PREFIX",
]


@pytest.fixture(autouse=True)
def _clear_config_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test starts with a clean configuration environment."""
    for key in _LLM_ENV_KEYS + _EMAIL_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# LLMConfig
# ---------------------------------------------------------------------------


def test_llm_defaults_and_legacy_openai_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default provider is openai and legacy OPENAI_* values are mapped."""
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-api-key")
    monkeypatch.setenv("OPENAI_API_URL", "https://api.openai.com/v1/")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")

    config = LLMConfig()

    assert config.llm_provider == "openai"
    assert config.llm_api_key == "legacy-api-key"
    assert config.llm_base_url == "https://api.openai.com/v1/"
    assert config.llm_model == "gpt-4-turbo"
    assert config.llm_timeout == 60.0


def test_llm_llm_vars_take_precedence_over_legacy_openai_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM_* values override OPENAI_* values when both are present."""
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-key")
    monkeypatch.setenv("OPENAI_API_URL", "https://legacy.openai.com/v1/")
    monkeypatch.setenv("OPENAI_MODEL", "legacy-model")

    monkeypatch.setenv("LLM_API_KEY", "new-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1/")
    monkeypatch.setenv("LLM_MODEL", "gpt-4-turbo")
    monkeypatch.setenv("LLM_TIMEOUT", "120.0")

    config = LLMConfig()

    assert config.llm_provider == "openai"
    assert config.llm_api_key == "new-key"
    assert config.llm_base_url == "https://api.openai.com/v1/"
    assert config.llm_model == "gpt-4-turbo"
    assert config.llm_timeout == 120.0


def test_llm_ollama_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ollama provider fills in local defaults for timeout, api key, and base url."""
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:latest")

    config = LLMConfig()

    assert config.llm_provider == "ollama"
    assert config.llm_base_url == "http://localhost:11434/v1/"
    assert config.llm_api_key == "ollama"
    assert config.llm_timeout == 60.0
    assert config.llm_model == "llama3.1:latest"


def test_llm_ollama_custom_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ollama custom values are preserved when supplied."""
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_BASE_URL", "http://host:11434/v1/")
    monkeypatch.setenv("LLM_API_KEY", "custom-key")
    monkeypatch.setenv("LLM_MODEL", "mistral:latest")
    monkeypatch.setenv("LLM_TIMEOUT", "90")

    config = LLMConfig()

    assert config.llm_base_url == "http://host:11434/v1/"
    assert config.llm_api_key == "custom-key"
    assert config.llm_model == "mistral:latest"
    assert config.llm_timeout == 90.0


def test_llm_openai_missing_required_fields() -> None:
    """OpenAI provider raises when required fields are missing."""
    with pytest.raises(ValidationError):
        LLMConfig()


def test_llm_ollama_missing_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ollama provider raises when llm_model is missing."""
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    with pytest.raises(ValidationError):
        LLMConfig()


def test_llm_invalid_timeout_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-numeric LLM timeout raises a validation error."""
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_API_URL", "https://api.openai.com/v1/")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4")
    monkeypatch.setenv("LLM_TIMEOUT", "not-a-number")

    with pytest.raises(ValidationError):
        LLMConfig()


# ---------------------------------------------------------------------------
# EmailConfig
# ---------------------------------------------------------------------------


def test_email_defaults_and_legacy_generic_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default provider is generic and legacy IMAP/EMAIL values are mapped."""
    monkeypatch.setenv("IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("EMAIL_USERNAME", "user@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")
    monkeypatch.setenv("FOLDER_PREFIX", "AI-")

    config = EmailConfig()

    assert config.email_provider == "generic"
    assert config.imap_host == "imap.example.com"
    assert config.imap_port == 993
    assert config.imap_use_ssl is True
    assert config.email_username == "user@example.com"
    assert config.email_password == "secret"
    assert config.folder_prefix == "AI-"


def test_email_generic_missing_credentials() -> None:
    """Generic IMAP provider raises when host or credentials are missing."""
    with pytest.raises(ValidationError):
        EmailConfig()


def test_email_gmail_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gmail provider loads username, app password, and label prefix."""
    monkeypatch.setenv("EMAIL_PROVIDER", "gmail")
    monkeypatch.setenv("GMAIL_USERNAME", "user@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "gmail-app-pw")
    monkeypatch.setenv("GMAIL_LABEL_PREFIX", "AI-")

    config = EmailConfig()

    assert config.email_provider == "gmail"
    assert config.gmail_username == "user@gmail.com"
    assert config.gmail_app_password == "gmail-app-pw"
    assert config.gmail_label_prefix == "AI-"
    assert config.folder_prefix == "AI-"


def test_email_yahoo_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Yahoo provider loads username, app password, and folder prefix."""
    monkeypatch.setenv("EMAIL_PROVIDER", "yahoo")
    monkeypatch.setenv("YAHOO_USERNAME", "user@yahoo.com")
    monkeypatch.setenv("YAHOO_APP_PASSWORD", "yahoo-app-pw")
    monkeypatch.setenv("YAHOO_FOLDER_PREFIX", "AI-Mail-")
    monkeypatch.setenv("FOLDER_PREFIX", "AI-")

    config = EmailConfig()

    assert config.email_provider == "yahoo"
    assert config.yahoo_username == "user@yahoo.com"
    assert config.yahoo_app_password == "yahoo-app-pw"
    assert config.yahoo_folder_prefix == "AI-Mail-"
    assert config.folder_prefix == "AI-"


def test_email_invalid_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-integer IMAP port raises a validation error."""
    monkeypatch.setenv("IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("EMAIL_USERNAME", "user@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")
    monkeypatch.setenv("IMAP_PORT", "not-a-port")

    with pytest.raises(ValidationError):
        EmailConfig()


def test_email_invalid_use_ssl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-boolean IMAP_USE_SSL raises a validation error."""
    monkeypatch.setenv("IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("EMAIL_USERNAME", "user@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")
    monkeypatch.setenv("IMAP_USE_SSL", "not-a-bool")

    with pytest.raises(ValidationError):
        EmailConfig()


def test_email_gmail_missing_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gmail provider raises when username or app password is missing."""
    monkeypatch.setenv("EMAIL_PROVIDER", "gmail")

    with pytest.raises(ValidationError):
        EmailConfig()


def test_email_yahoo_missing_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Yahoo provider raises when username or app password is missing."""
    monkeypatch.setenv("EMAIL_PROVIDER", "yahoo")

    with pytest.raises(ValidationError):
        EmailConfig()
