"""Unit tests for the OpenAI client."""

from unittest.mock import MagicMock

import openai
import pytest
from pytest_mock import MockerFixture

from ai.openai_client import OpenAIClient
from config import LLMConfig


@pytest.fixture(autouse=True)
def _set_folder_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure FOLDER_PREFIX is set for prompt generation."""
    monkeypatch.setenv("FOLDER_PREFIX", "AI-")


def _make_config(**overrides):
    defaults = {
        "llm_provider": "openai",
        "llm_base_url": "https://api.openai.com/v1/",
        "llm_api_key": "test-key",
        "llm_model": "gpt-4",
    }
    defaults.update(overrides)
    return LLMConfig(**defaults)


def _set_response(mock_openai: MagicMock, content: str, headers: dict | None = None) -> MagicMock:
    raw = MagicMock()
    raw.headers = headers or {}
    raw.parse.return_value.choices = [MagicMock(message=MagicMock(content=content))]
    mock_openai.return_value.chat.completions.with_raw_response.create.return_value = raw
    return raw


def test_configure_uses_openai_client(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    client = OpenAIClient()
    client.configure(_make_config(llm_timeout=30.0))
    mock_openai.assert_called_once_with(
        base_url="https://api.openai.com/v1/",
        api_key="test-key",
        timeout=30.0,
    )


def test_classify_email_valid(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    _set_response(mock_openai, "Personal: this is personal")
    client = OpenAIClient()
    client.configure(_make_config())
    folder, explanation = client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["AI-Personal", "AI-Important"],
    )
    assert folder == "AI-Personal"
    assert explanation == "this is personal"


def test_classify_email_inbox(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    _set_response(mock_openai, "Inbox: keep here")
    client = OpenAIClient()
    client.configure(_make_config())
    folder, explanation = client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["AI-Personal"],
    )
    assert folder == "Inbox"
    assert explanation == "keep here"


def test_classify_email_rate_limits(capsys, mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    _set_response(mock_openai, "Inbox: ok", headers={"x-ratelimit-limit-requests": "100"})
    client = OpenAIClient()
    client.configure(_make_config())
    client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["AI-Personal"],
        show_rate_limits=True,
    )
    captured = capsys.readouterr()
    assert "Rate Limit Requests" in captured.out
    assert "100" in captured.out


def test_classify_email_api_error(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    mock_openai.return_value.chat.completions.with_raw_response.create.side_effect = openai.APIConnectionError(
        message="network down", request=None
    )
    client = OpenAIClient()
    client.configure(_make_config())
    folder, explanation = client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["AI-Personal"],
    )
    assert folder == "invalid"
    assert "network down" in explanation


def test_health_check_success(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    client = OpenAIClient()
    client.configure(_make_config())
    mock_openai.return_value.models.list.return_value = []
    assert client.health_check() is True


def test_health_check_failure(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    client = OpenAIClient()
    client.configure(_make_config())
    mock_openai.return_value.models.list.side_effect = openai.APIConnectionError(
        message="down", request=None
    )
    assert client.health_check() is False


def test_classify_email_json_mode(mocker: MockerFixture):
    mock_openai = mocker.patch("openai.OpenAI")
    _set_response(mock_openai, '{"folder": "Personal", "explanation": "this is personal"}')
    client = OpenAIClient()
    client.configure(_make_config())
    folder, explanation = client.classify_email(
        {"subject": "S", "from": "a@b.com", "body": "B"},
        ["AI-Personal", "AI-Important"],
        use_json_mode=True,
    )
    assert folder == "AI-Personal"
    assert explanation == "this is personal"
    create = mock_openai.return_value.chat.completions.with_raw_response.create
    assert create.call_count == 1
    assert create.call_args.kwargs.get("response_format") == {"type": "json_object"}
