"""Unit tests for src/ai.py."""

from unittest.mock import MagicMock

import pytest

import ai


@pytest.fixture
def set_ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables used by the ai module."""
    monkeypatch.setenv("FOLDER_PREFIX", "AI-")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")


def test_configure_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    import openai
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_URL", "https://api.openai.com/v1/")
    ai.configure_openai()
    assert openai.api_key == "test-key"
    assert openai.base_url == "https://api.openai.com/v1/"


def test_generate_prompt(set_ai_env: None) -> None:
    message = {
        "subject": "Hello",
        "from": "sender@example.com",
        "body": "This is the body.",
    }
    system_prompt, prompt = ai.generate_prompt(message, ["AI-Work", "AI-Personal"])
    assert "Work" in system_prompt
    assert "Personal" in system_prompt
    assert "Hello" in prompt
    assert "This is the body" in prompt


def test_generate_prompt_show_prompt(capsys, set_ai_env: None) -> None:
    message = {
        "subject": "Hello",
        "from": "sender@example.com",
        "body": "This is the body.",
    }
    ai.generate_prompt(message, ["AI-Work"], show_prompt=True)
    captured = capsys.readouterr()
    assert "Hello" in captured.out


def test_get_ai_response_valid(
    set_ai_env: None, mock_openai_client: MagicMock
) -> None:
    mock_openai_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="Work: this is work"))
    ]
    folder, explanation = ai.get_ai_response(
        "prompt", "system", ["Work", "Personal"], show_rate_limits=False
    )
    assert folder == "Work"
    assert explanation == "this is work"


def test_get_ai_response_inbox(
    set_ai_env: None, mock_openai_client: MagicMock
) -> None:
    mock_openai_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="Inbox: keep here"))
    ]
    folder, explanation = ai.get_ai_response(
        "prompt", "system", ["Work", "Personal"], show_rate_limits=False
    )
    assert folder == "Inbox"
    assert explanation == "keep here"


def test_get_ai_response_invalid_no_colon(
    set_ai_env: None, mock_openai_client: MagicMock
) -> None:
    mock_openai_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="nonsense"))
    ]
    folder, explanation = ai.get_ai_response(
        "prompt", "system", ["Work", "Personal"], show_rate_limits=False
    )
    assert folder == "invalid"
    assert "could not split" in explanation


def test_get_ai_response_unknown_folder(
    set_ai_env: None, mock_openai_client: MagicMock
) -> None:
    mock_openai_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="Bogus: not a folder"))
    ]
    folder, explanation = ai.get_ai_response(
        "prompt", "system", ["Work", "Personal"], show_rate_limits=False
    )
    assert 'invalid: "Bogus"' == folder
    assert explanation == "not a folder"


def test_get_ai_response_rate_limits(
    set_ai_env: None, mock_openai_client: MagicMock, capsys
) -> None:
    mock_openai_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="Inbox: ok"))
    ]
    mock_openai_client.return_value.headers.get.return_value = "100"
    ai.get_ai_response("prompt", "system", ["Work"], show_rate_limits=True)
    captured = capsys.readouterr()
    assert "Rate Limit Requests" in captured.out


def test_get_ai_response_api_error(
    set_ai_env: None, mock_openai_client: MagicMock
) -> None:
    mock_openai_client.side_effect = Exception("network down")
    with pytest.raises(SystemExit):
        ai.get_ai_response("prompt", "system", ["Work"], show_rate_limits=False)


def test_get_ai_response_from_message(
    set_ai_env: None, mock_openai_client: MagicMock
) -> None:
    mock_openai_client.return_value.parse.return_value.choices = [
        MagicMock(message=MagicMock(content="Inbox: keep"))
    ]
    message = {
        "subject": "Hello",
        "from": "sender@example.com",
        "body": "Body",
    }
    folder, explanation = ai.get_ai_response_from_message(
        message, ["AI-Work"], show_prompt=False, show_rate_limits=False
    )
    assert folder == "Inbox"
    assert explanation == "keep"
