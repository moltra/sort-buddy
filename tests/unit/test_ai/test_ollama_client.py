"""Unit tests for the Ollama client."""

from unittest.mock import MagicMock

import openai
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


def test_classify_email_text_mode_still_works(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    _set_response(mock_openai, "  Important  :  because  ")
    client = OllamaClient()
    client.configure(_make_config())
    folder, explanation = client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["AI-Important", "AI-Personal"],
        use_json_mode=False,
    )
    assert folder == "AI-Important"
    assert explanation == "because"


def test_classify_email_json_mode_valid(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    _set_response(mock_openai, '{"folder": "Newsletters", "explanation": "Marketing content."}')
    client = OllamaClient()
    client.configure(_make_config())
    folder, explanation = client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["AI-Newsletters", "AI-Important"],
        use_json_mode=True,
    )
    assert folder == "AI-Newsletters"
    assert explanation == "Marketing content."
    call_kwargs = mock_openai.return_value.chat.completions.with_raw_response.create.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}


def test_classify_email_json_mode_invalid_json_fallback(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    _set_response(mock_openai, "Newsletters: fallback text")
    client = OllamaClient()
    client.configure(_make_config())
    folder, explanation = client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["AI-Newsletters", "AI-Important"],
        use_json_mode=True,
    )
    assert folder == "AI-Newsletters"
    assert explanation == "fallback text"


def test_classify_email_json_mode_extra_body_fallback(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    raw = MagicMock()
    raw.headers = {}
    raw.parse.return_value.choices = [MagicMock(message=MagicMock(content='{"folder": "Newsletters", "explanation": "ok."}'))]

    def side_effect(**kwargs):
        if "response_format" in kwargs:
            raise openai.BadRequestError(
                "response_format not supported",
                response=MagicMock(request=MagicMock()),
                body=None,
            )
        return raw

    mock_openai.return_value.chat.completions.with_raw_response.create.side_effect = side_effect
    client = OllamaClient()
    client.configure(_make_config())
    folder, explanation = client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["AI-Newsletters", "AI-Important"],
        use_json_mode=True,
    )
    assert folder == "AI-Newsletters"
    assert explanation == "ok."
    calls = mock_openai.return_value.chat.completions.with_raw_response.create.call_args_list
    assert calls[0].kwargs["response_format"] == {"type": "json_object"}
    assert calls[1].kwargs["extra_body"] == {"format": "json", "options": {"num_ctx": 8192}}
