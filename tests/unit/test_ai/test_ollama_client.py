"""Unit tests for the Ollama client."""

from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from ai.ollama_client import OllamaClient
from config import LLMConfig


@pytest.fixture(autouse=True)
def _set_folder_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure FOLDER_PREFIX is set for prompt generation."""
    monkeypatch.setenv("FOLDER_PREFIX", "AI-")


def _make_config(**overrides):
    defaults = {
        "llm_provider": "ollama",
        "llm_base_url": "http://localhost:11434/v1/",
        "llm_api_key": "",
        "llm_model": "llama3.1:latest",
    }
    defaults.update(overrides)
    return LLMConfig(**defaults)


def _set_response(mock_openai: MagicMock, content: str) -> MagicMock:
    raw = MagicMock()
    raw.headers = {}
    raw.parse.return_value.choices = [MagicMock(message=MagicMock(content=content))]
    mock_openai.return_value.chat.completions.with_raw_response.create.return_value = raw
    return raw


def test_configure_uses_ollama_defaults(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    client = OllamaClient()
    client.configure(_make_config(llm_timeout=60.0))
    mock_openai.assert_called_once_with(
        base_url="http://localhost:11434/v1/",
        api_key="ollama",
        timeout=60.0,
    )


def test_configure_uses_empty_api_key(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    client = OllamaClient()
    client.configure(_make_config(llm_api_key=""))
    call_kwargs = mock_openai.call_args.kwargs
    assert call_kwargs["api_key"] == "ollama"


def test_classify_email_robust_whitespace(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    _set_response(mock_openai, "  Work  :  because  ")
    client = OllamaClient()
    client.configure(_make_config())
    folder, explanation = client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["Work", "Personal"],
    )
    assert folder == "Work"
    assert explanation == "because"


def test_classify_email_no_colon(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    _set_response(mock_openai, "nonsense")
    client = OllamaClient()
    client.configure(_make_config())
    folder, explanation = client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["Work"],
    )
    assert folder == "invalid"
    assert "could not split" in explanation


def test_classify_email_no_rate_limit_output(capsys, mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    _set_response(mock_openai, "Inbox: ok")
    client = OllamaClient()
    client.configure(_make_config())
    client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["Work"],
        show_rate_limits=True,
    )
    captured = capsys.readouterr()
    assert "Rate Limit" not in captured.out


def test_health_check(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    client = OllamaClient()
    client.configure(_make_config())
    mock_openai.return_value.models.list.return_value = []
    assert client.health_check() is True
