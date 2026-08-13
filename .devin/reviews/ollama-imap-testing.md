# Testing Review: Ollama + IMAP Integration

**Review agent:** `testing-guardian`  
**Branch:** `feature/ollama-imap-integration`  
**Date:** 2026-08-12  
**Scope:** Existing tests, coverage, mocking strategy, and proposed test plan for adding Ollama (OpenAI-compatible API) and Gmail/Yahoo IMAP support.

---

## Executive Summary / Verdict

**Current state: FAIL** — Sort Buddy currently has **zero meaningful test coverage**. The `tests/` directory contains only an empty `__init__.py`. No unit, integration, or regression tests exist for the AI client, IMAP fetcher, JSON fetcher, utilities, or CLI entry point. Any implementation of Ollama and Gmail/Yahoo IMAP connectivity therefore needs to be accompanied by a **new, from-scratch test suite** with strict mocking discipline.

**Recommendation:** Block implementation from proceeding without a co-developed `pytest` suite and a minimum coverage gate for the changed modules.

---

## 1. Current Test Coverage

### 1.1 What is tested

Nothing is tested. The only item in `tests/` is:

- `tests/__init__.py` — empty file (line 0).

There are no `test_*.py` files, no `conftest.py`, no fixtures, and no parameterized test data.

### 1.2 Coverage by module

| Module | Lines | Has tests? | Notes |
|--------|------:|-----------:|-------|
| `src/ai.py` | 100 | No | OpenAI chat completions, prompt generation, response parsing. |
| `src/email_fetcher.py` | 102 | No | IMAP connection, search, fetch, parse, flag, move. |
| `src/json_email_fetcher.py` | 41 | No | File-based offline fetcher used by `--use-json`. |
| `src/main.py` | 114 | No | CLI, orchestration, `--dry-run`, `--save-to-json`. |
| `src/util.py` | 46 | No | Helpers for JSON output, decoding, linefeed limiting, terminal width, signal handling. |

### 1.3 `if __name__ == "__main__"` coverage

`src/main.py` lines 93–114 (`if __name__ == "__main__":` block) are untested. These lines parse CLI arguments, wire signal handlers, and bootstrap `main(...)`. They should be exercised with `pytest`’s `capsys`/`caplog` or by invoking `main()` with patched dependencies.

---

## 2. Existing Test Infrastructure and Dependencies

### 2.1 Build/test tooling

- Package manager: **Poetry** (`pyproject.toml`).
- `package-mode = false` (script-style project).
- Python requirement: `^3.10`.

### 2.2 Production dependencies relevant to testing

| Dependency | Version | Relevance |
|------------|---------|-----------|
| `openai` | `^1.26.0` | Chat completions API; must be mocked at the client or transport layer. |
| `imapclient` | `^3.0.1` | IMAP protocol; must be mocked at `IMAPClient` class level. |
| `mail-parser` | `^3.15.0` | Listed but not imported in current source; verify usage before writing tests. |
| `beautifulsoup4` / `lxml` | — | HTML→text extraction; can be exercised directly. |
| `colorama` | — | Terminal styling; generally safe but may need `capsys` assertions. |
| `python-dotenv` | — | Loads `.env`; tests should patch `os.environ` or use `monkeypatch`. |

### 2.3 Missing test dependencies

The following should be added to `[tool.poetry.dependencies]` or a dedicated `[tool.poetry.group.test.dependencies]` group:

- `pytest` — test runner.
- `pytest-mock` — `mocker` fixture and scoped patching.
- `pytest-cov` — coverage reporting.
- `pytest-asyncio` — only if async code is introduced later; currently not needed.
- `responses` or `pytest-httpx` — optional if the project later switches to raw HTTP calls; for now `openai` calls can be mocked via `mocker.patch.object`.

**Action item:** Add `pytest`, `pytest-mock`, and `pytest-cov` to `pyproject.toml` before writing tests.

---

## 3. Issues with Current Code That Affect Testability

The following testability risks are observed in source code. They are not the focus of this review, but they determine how tests must be structured.

### 3.1 Module-level `load_dotenv()` in `src/main.py`

`load_dotenv()` is called at module import time (line 12). In tests this can cause real environment variables to leak into test fixtures. Prefer:

```python
# In tests
monkeypatch.setenv("OPENAI_API_KEY", "test-key")
# or patch dotenv.load_dotenv before importing main
```

### 3.2 Global `openai` client mutation in `src/ai.py`

`configure_openai()` sets `openai.api_key` and `openai.base_url` as module globals (lines 4–6). Tests should either:

- Patch `openai.chat.completions.with_raw_response.create` directly, **or**
- Refactor to accept a client instance so tests can inject a fake client.

### 3.3 IMAP connection inside `EmailFetcher.__init__`

`EmailFetcher.__init__` performs network I/O (lines 15–20):

```python
self.imapclient = IMAPClient(self.host, ssl=True)
self.imapclient.login(...)
self.imapclient.select_folder('INBOX', readonly=False)
self.unseen_ids = self.search_unseen_without_flag('SortBuddy')
```

This makes it impossible to instantiate the class in a unit test without first connecting to a real IMAP server. Tests must either:

- Patch `imapclient.IMAPClient` before `EmailFetcher` is instantiated, or
- Refactor construction to separate *configuration* from *connection* (recommended).

### 3.4 `exit()` on OpenAI error

`src/ai.py` line 77 calls `exit()` inside `get_ai_response()`. This terminates the test runner. Tests for the error path must either:

- Assert that the exception is raised and catch it with `pytest.raises(SystemExit)`, or
- Refactor to raise a domain-specific exception instead of `exit()`.

### 3.5 No separation between transport and business logic

`EmailFetcher` mixes IMAP transport, email parsing, HTML conversion, and side effects (flag/unseen/move). Unit tests will require many carefully-scoped mocks unless these responsibilities are split.

---

## 4. Mocking Strategy for IMAP and OpenAI/Ollama

### 4.1 IMAP mocking (`imapclient`)

**Preferred approach:** patch the `IMAPClient` class at the `email_fetcher` module level so each test receives a fresh mock instance.

```python
import pytest

@pytest.fixture
def mock_imap(mocker):
    MockIMAP = mocker.patch("email_fetcher.IMAPClient")
    client = MockIMAP.return_value
    # default happy-path data
    client.list_folders.return_value = [
        (b"\\HasNoChildren", b"/", "AI-Important"),
        (b"\\HasNoChildren", b"/", "AI-Spam"),
        (b"\\HasNoChildren", b"/", "INBOX"),
    ]
    client.search.return_value = [101, 102]
    client.fetch.return_value = {
        101: {
            b"ENVELOPE": make_envelope(subject=b"Test"),
            b"RFC822": raw_email_bytes(...),
            b"BODY[TEXT]": b"hello world",
        }
    }
    yield client
```

**Scope rules:**

- Always use `mocker.patch("email_fetcher.IMAPClient")` rather than monkey-patching `imapclient.imapclient.IMAPClient` globally.
- Never connect to `imap.gmail.com` or `imap.mail.yahoo.com` in unit tests.
- Use small, realistic `RFC822` byte samples stored in `tests/fixtures/emails/` rather than hand-crafting every byte array.

### 4.2 OpenAI / Ollama chat-completion mocking

Because Ollama will be accessed through the **OpenAI-compatible endpoint**, the existing `openai.chat.completions.with_raw_response.create` call does not need to change if the configuration only swaps the `base_url` and `model`. Tests should therefore mock the **same call path** and parameterize the fake base URL/model to exercise both providers.

**Preferred approach:** patch `openai.chat.completions.with_raw_response.create` and return a fake `LegacyAPIResponse`-like object.

```python
@pytest.fixture
def mock_openai(mocker):
    fake_response = mocker.MagicMock()
    fake_response.headers = {"x-ratelimit-limit-requests": "1000"}
    parsed = mocker.MagicMock()
    parsed.choices = [mocker.MagicMock()]
    parsed.choices[0].message.content = "AI-Important: looks important"
    fake_response.parse.return_value = parsed
    yield mocker.patch(
        "ai.openai.chat.completions.with_raw_response.create",
        return_value=fake_response,
    )
```

**Important:** Use `mocker.MagicMock()` here only as a **shape**; tests should assert on concrete return values (e.g., `assert folder == "AI-Important"`).

For Ollama specifically, add tests that verify:

- `base_url` ends with `/v1/` (Ollama OpenAI-compatible requirement).
- Rate-limit headers may be absent; `show_rate_limits` should not crash.
- Response parsing still splits on `: `.

### 4.3 Environment mocking

Use `monkeypatch.setenv` (or `mocker.patch.dict(os.environ, ...)`) for:

- `OPENAI_API_KEY`
- `OPENAI_API_URL`
- `OPENAI_MODEL`
- `FOLDER_PREFIX`
- `IMAP_HOST`
- `EMAIL_USERNAME`
- `EMAIL_PASSWORD`

Never rely on a real `.env` file in CI.

---

## 5. Recommended Tests for New IMAP Providers (Gmail, Yahoo)

### 5.1 Provider-specific configuration tests

| Test | What it verifies |
|------|-----------------|
| `test_gmail_default_host_is_imap_gmail_com` | When provider is `gmail`, default `IMAP_HOST` resolves to `imap.gmail.com`. |
| `test_yahoo_default_host_is_imap_mail_yahoo_com` | When provider is `yahoo`, default host is `imap.mail.yahoo.com`. |
| `test_generic_provider_uses_custom_host` | Custom `IMAP_HOST` is respected when provider is `generic`. |
| `test_gmail_requires_app_password` | Configuration validation rejects a plain Gmail web password (security/planner concern). |
| `test_provider_env_var_defaults_to_generic` | Backward compatibility: missing `IMAP_PROVIDER` still uses `IMAP_HOST`. |

### 5.2 Provider-specific IMAP behavior tests

Gmail and Yahoo have subtle differences:

| Test | Why it matters |
|------|--------------|
| `test_gmail_xlist_folders` | Gmail exposes labels with `XLIST`; `list_ai_folders()` must filter correctly. |
| `test_yahoo_folder_delimiter` | Yahoo folder delimiter may differ; `list_ai_folders()` should not hard-code `/`. |
| `test_gmail_copy_then_delete_is_move` | Gmail `MOVE` extension support varies; verify fallback path. |
| `test_provider_ssl_required` | Both providers reject non-SSL connections; test `ssl=True` is passed. |
| `test_oauth_vs_password_flow` | If OAuth2 is added later, test provider selection branches. |

**Mocking note:** Provider-specific tests should *not* hit real servers. The mocked `IMAPClient` should be configured with representative `list_folders()` return shapes for each provider.

### 5.3 Error-path tests

- `test_imap_login_failure_raises` — mock `login` raising `IMAPClient.Error`.
- `test_imap_folder_select_failure` — mock `select_folder` raising.
- `test_imap_search_timeout` — mock `search` raising socket/timeout error.
- `test_move_message_failure_catches_exception` — `move_message` already has a broad `except Exception`; test it logs and does not crash.

---

## 6. Recommended Tests for Ollama Endpoint

### 6.1 Configuration

- `test_ollama_base_url_defaults_to_localhost_v1`
- `test_ollama_model_defaults_to_sensible_local_model`
- `test_openai_url_still_works_when_base_url_is_openai`
- `test_missing_api_key_for_ollama_is_allowed` — Ollama often runs without a key.

### 6.2 Chat-completion behavior

- `test_ollama_response_parses_folder_and_explanation` — same split logic as OpenAI.
- `test_ollama_empty_response_returns_invalid` — model returns empty string.
- `test_ollama_response_without_colon_returns_invalid` — falls into `ValueError` branch.
- `test_ollama_rate_limit_headers_are_absent` — `show_rate_limits` does not crash when headers are missing.
- `test_ollama_timeout_is_handled` — mock `create` raising `openai.APITimeoutError`.

### 6.3 Prompt tests (provider-agnostic)

- `test_generate_prompt_includes_all_stripped_folders`
- `test_generate_prompt_ends_with_body`
- `test_generate_prompt_without_folder_prefix_unchanged`
- `test_get_stripped_folder_list_removes_prefix`

---

## 7. Testing Without Real Credentials

### 7.1 Unit-test discipline

Every test should pass with:

- `OPENAI_API_KEY` unset or set to a dummy value.
- No network access to `api.openai.com`, `localhost:11434`, or any IMAP host.
- No `.env` file present.

Enforce this in CI by running:

```bash
poetry run pytest --disable-socket
```

If `--disable-socket` is not available, add the `pytest-socket` plugin to test dependencies.

### 7.2 Fixture data

Create `tests/fixtures/`:

```
tests/
├── __init__.py
├── conftest.py
├── fixtures/
│   ├── emails/
│   │   ├── plain_text.eml
│   │   ├── html_only.eml
│   │   └── multipart.eml
│   └── responses/
│       ├── openai_valid.json
│       ├── ollama_valid.json
│       └── invalid_no_colon.json
└── unit/
    ├── test_ai.py
    ├── test_email_fetcher.py
    ├── test_json_email_fetcher.py
    ├── test_util.py
    └── test_main.py
```

### 7.3 Credential hygiene in tests

- Never place real API keys, passwords, or tokens in fixtures.
- Use `FAKE-IMAP-PASSWORD` style placeholders.
- Assert that `IMAPClient.login` is called with environment-derived credentials, not literal secrets.

---

## 8. Proposed Test Plan for Implementation Phase

### Wave 0: Bootstrap tooling (before feature code)

1. Add test dependencies to `pyproject.toml`:
   - `pytest`
   - `pytest-mock`
   - `pytest-cov`
   - `pytest-socket` (optional but recommended)
2. Run `poetry lock --no-update` and `poetry install`.
3. Add `pytest.ini` or `[tool.pytest.ini_options]` with defaults:
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   addopts = "-v --cov=src --cov-report=term-missing --disable-socket"
   ```
4. Create `tests/conftest.py` with shared fixtures for:
   - mocked OpenAI response
   - mocked `IMAPClient`
   - sample messages and folders
   - patched environment variables

### Wave 1: Back-fill unit tests for existing modules

Order matters: test utility/pure functions first, then modules with side effects.

1. `tests/unit/test_util.py`
   - `remove_prefix`
   - `get_stripped_folder_list`
   - `limit_consecutive_linefeeds`
   - `safe_decode` (UTF-8, latin-1 fallback, invalid bytes)
   - `save_results_to_json`
   - `get_terminal_width` (mock `os.get_terminal_size`)
2. `tests/unit/test_ai.py`
   - `configure_openai`
   - `generate_prompt`
   - `get_ai_response` happy path and all error paths
   - `get_ai_response_from_message`
3. `tests/unit/test_json_email_fetcher.py`
   - `list_ai_folders`
   - `fetch_next_message`
   - `has_more_messages`
   - `move_message` / `set_unseen` / `close` no-ops
4. `tests/unit/test_email_fetcher.py`
   - construction/login/search/fetch mocked end-to-end
   - `list_ai_folders` filtering
   - multipart parsing
   - flag/unseen/move side effects
5. `tests/unit/test_main.py`
   - `main()` happy path with both fetchers
   - `--dry-run`
   - `--limit`
   - `--save-to-json`
   - `--show-prompt`
   - `--print-rate-limits`
   - `if __name__ == "__main__"` block via `pytest` or `subprocess`

### Wave 2: Tests for IMAP provider support (Gmail, Yahoo)

1. Add provider configuration abstraction if the planner introduces one.
2. Add tests listed in Section 5.1 and 5.2.
3. Add error-path tests from Section 5.3.

### Wave 3: Tests for Ollama endpoint

1. Add Ollama-specific tests from Section 6.
2. Parameterize OpenAI vs. Ollama tests where behavior is identical.
3. Verify no real HTTP calls with `pytest-socket`.

### Wave 4: Integration / smoke tests (optional, local only)

1. Provide a `tests/integration/` directory with tests **skipped by default**:
   - `@pytest.mark.integration`
   - `@pytest.mark.skipif(not os.getenv("OLLAMA_HOST"), ...)`
   - `@pytest.mark.skipif(not os.getenv("IMAP_HOST"), ...)`
2. Document in `README.md` how to run them locally with real credentials.
3. CI must **not** run integration tests automatically.

### Wave 5: Coverage gate and CI

1. Set a minimum coverage threshold for modified modules:
   - Start with `80%` for `src/ai.py`, `src/email_fetcher.py`, and `src/main.py`.
2. Add a GitHub Actions / CI step:
   ```yaml
   - run: poetry run pytest --cov=src --cov-report=xml --cov-fail-under=80
   ```
3. Fail builds on uncovered new code.

---

## 9. Test Quality Guidelines for Implementers

Adhere to these rules when writing the new tests:

- **Single responsibility:** one concept per test function.
- **Descriptive names:** `test_generate_prompt_appends_email_body`, not `test_ai_1`.
- **Concrete assertions:** assert exact values, not `assert result is not None`.
- **Arrange-Act-Assert** structure.
- **Prefer `mocker.patch()`** over manual `setattr`/monkeypatch.
- **Scope mocks** to the module under test, not to third-party internals.
- **Use fixtures** for repeated setup (mock clients, sample messages, env vars).
- **No real network:** every unit test must pass with `--disable-socket`.
- **Parametrize** provider variants (OpenAI vs. Ollama, Gmail vs. Yahoo vs. generic).
- **Do not test implementation internals** unless necessary; test observable behavior.

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------:|-------:|-----------|
| IMAP constructor performs network I/O, making unit tests hard to write. | High | High | Refactor `EmailFetcher` to separate configuration and connection; or patch `IMAPClient` in every test. |
| `exit()` in `ai.py` crashes pytest. | Medium | Medium | Replace `exit()` with raised exception and handle it in `main()`. |
| `load_dotenv()` at import time affects test env. | Medium | Medium | Patch `dotenv.load_dotenv` before importing `main`, or move call inside `main()`. |
| MagicMock-only tests pass for wrong reasons. | Medium | Medium | Always assert on concrete return values and call counts. |
| Gmail/Yahoo folder formats differ and are not captured by mocks. | Medium | Medium | Store provider-specific fixture data and validate filtering logic. |
| Ollama rate-limit headers absent; `show_rate_limits` crashes. | Low | Medium | Add test for missing headers. |

---

## 11. Final Verdict

**FAIL** on current coverage, with a clear remediation path.

The project has no tests today. The Ollama/IMAP feature must be implemented **together with** a new pytest-based test suite. The biggest blockers to testability are the IMAP connection in `EmailFetcher.__init__` and the `exit()` call in `src/ai.py`; the planner should address these before or during implementation. Once those are fixed, the recommended test plan above can be executed to achieve robust, isolated, credential-free unit tests for OpenAI/Ollama and Gmail/Yahoo/generic IMAP providers.
