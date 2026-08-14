"""Unit tests for prompt building and response parsing."""

from ai import prompts


EXPECTED_FOLDERS = {"Important", "Newsletters", "Notifications", "Other", "Personal", "Spam"}


def _set_prefix(monkeypatch):
    monkeypatch.setenv("FOLDER_PREFIX", "AI-")


def test_folder_definitions_has_all_six_folders():
    assert set(prompts.FOLDER_DEFINITIONS.keys()) == EXPECTED_FOLDERS


def test_generate_prompt_includes_folders(monkeypatch):
    _set_prefix(monkeypatch)
    message = {"subject": "Hello", "from": "a@b.com", "body": "Body"}
    all_folders = [f"AI-{name}" for name in EXPECTED_FOLDERS]
    system, user = prompts.generate_prompt(message, all_folders)
    for name in EXPECTED_FOLDERS:
        assert name in system
    assert "Negative examples" in system
    assert "Hello" in user
    assert "Body" in user


def test_generate_prompt_show_prompt(capsys, monkeypatch):
    _set_prefix(monkeypatch)
    message = {"subject": "Hello", "from": "a@b.com", "body": "Body"}
    prompts.generate_prompt(message, ["AI-Other"], show_prompt=True)
    captured = capsys.readouterr()
    assert "Hello" in captured.out


def test_generate_json_prompt_includes_folders(monkeypatch):
    _set_prefix(monkeypatch)
    message = {"subject": "Hello", "from": "a@b.com", "body": "Body"}
    all_folders = [f"AI-{name}" for name in EXPECTED_FOLDERS]
    system, user = prompts.generate_json_prompt(message, all_folders)
    for name in EXPECTED_FOLDERS:
        assert name in system
    assert '{"folder":' in system
    assert "Hello" in user
    assert "Body" in user


def test_parse_classification_valid():
    assert prompts.parse_classification("Important: because", ["Important", "Personal"]) == ("Important", "because")


def test_parse_classification_inbox():
    assert prompts.parse_classification("Inbox: keep", ["Important"]) == ("Inbox", "keep")


def test_parse_classification_no_colon():
    assert prompts.parse_classification("nonsense", ["Important"]) == ("invalid", "could not split response")


def test_parse_classification_unknown_folder():
    folder, explanation = prompts.parse_classification("Bogus: not a folder", ["Important", "Personal"])
    assert 'invalid: "Bogus"' == folder
    assert explanation == "not a folder"


def test_parse_classification_ignores_whitespace():
    assert prompts.parse_classification("  Important  :  because  ", ["Important", "Personal"]) == ("Important", "because")


def test_parse_json_classification_valid():
    content = '{"folder": "Newsletters", "explanation": "This is a newsletter."}'
    assert prompts.parse_json_classification(content, ["AI-Newsletters", "AI-Important"]) == ("AI-Newsletters", "This is a newsletter.")


def test_parse_json_classification_with_prefix():
    content = '{"folder": "AI-Notifications", "explanation": "Automated alert."}'
    assert prompts.parse_json_classification(content, ["AI-Notifications", "AI-Important"]) == ("AI-Notifications", "Automated alert.")


def test_parse_json_classification_markdown_fence():
    content = '```json\n{"folder": "Spam", "explanation": "Unsolicited."}\n```'
    assert prompts.parse_json_classification(content, ["AI-Spam", "AI-Important"]) == ("AI-Spam", "Unsolicited.")


def test_parse_json_classification_invalid_json_fallback():
    content = "Newsletters: fallback text"
    assert prompts.parse_json_classification(content, ["AI-Newsletters", "AI-Important"]) == ("AI-Newsletters", "fallback text")


def test_parse_json_classification_missing_fields():
    content = '{"folder": "Newsletters"}'
    folder, explanation = prompts.parse_json_classification(content, ["AI-Newsletters", "AI-Important"])
    assert folder.startswith("invalid")
