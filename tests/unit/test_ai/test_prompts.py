"""Unit tests for prompt building and response parsing."""

from ai import prompts


def _set_prefix(monkeypatch):
    monkeypatch.setenv("FOLDER_PREFIX", "AI-")


def test_generate_prompt_includes_folders(monkeypatch):
    _set_prefix(monkeypatch)
    message = {"subject": "Hello", "from": "a@b.com", "body": "Body"}
    system, user = prompts.generate_prompt(message, ["AI-Work", "AI-Personal"])
    assert "Work" in system
    assert "Personal" in system
    assert "Hello" in user
    assert "Body" in user


def test_generate_prompt_show_prompt(capsys, monkeypatch):
    _set_prefix(monkeypatch)
    message = {"subject": "Hello", "from": "a@b.com", "body": "Body"}
    prompts.generate_prompt(message, ["AI-Work"], show_prompt=True)
    captured = capsys.readouterr()
    assert "Hello" in captured.out


def test_parse_classification_valid():
    assert prompts.parse_classification("Work: because", ["Work", "Personal"]) == ("Work", "because")


def test_parse_classification_inbox():
    assert prompts.parse_classification("Inbox: keep", ["Work"]) == ("Inbox", "keep")


def test_parse_classification_no_colon():
    assert prompts.parse_classification("nonsense", ["Work"]) == ("invalid", "could not split response")


def test_parse_classification_unknown_folder():
    folder, explanation = prompts.parse_classification("Bogus: not a folder", ["Work", "Personal"])
    assert 'invalid: "Bogus"' == folder
    assert explanation == "not a folder"


def test_parse_classification_ignores_whitespace():
    assert prompts.parse_classification("  Work  :  because  ", ["Work", "Personal"]) == ("Work", "because")
