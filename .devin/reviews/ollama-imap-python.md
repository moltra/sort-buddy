# Python Code Review: Ollama/IMAP Integration

**Project:** Sort Buddy  
**Branch:** `feature/ollama-imap-integration`  
**Reviewer:** python-reviewer sub-agent  
**Date:** 2026-08-12  
**Scope:** All Python source files in `src/` directory

---

## Summary

The Sort Buddy codebase is a small, focused email classification application consisting of ~300 lines of Python across 5 modules. The code is generally straightforward but has several critical issues that must be addressed before implementing Ollama and IMAP provider support. Key concerns include: complete lack of type hints, naked exception handling, no error recovery for network operations, missing validation of environment variables, and a brittle OpenAI client integration that will require significant refactoring for Ollama compatibility. The codebase has no tests (empty `tests/` directory), which is a significant risk for network-dependent features.

---

## Critical Issues

### 1. Naked Exception Handling with Silent Failure

**File:** `src/ai.py`  
**Lines:** 75-77  
**Severity:** CRITICAL

```python
except Exception as e:
    print(f"Error in calling OpenAI API: {e}")
    exit()
```

**Issue:** Catching the base `Exception` class and calling `exit()` is an anti-pattern. This:
- Prevents any error recovery or retry logic
- Provides no stack trace for debugging
- Abruptly terminates the program without cleanup
- Makes the application unusable in batch/automated contexts

**Recommendation:** Catch specific exceptions (`openai.APIError`, `openai.RateLimitError`, `openai.APITimeoutError`, `ConnectionError`) and implement retry logic with exponential backoff. Log full stack traces using `logging` module instead of `print`. Raise exceptions to caller for handling.

---

### 2. IMAP Connection Failure Not Handled

**File:** `src/email_fetcher.py`  
**Lines:** 15-17  
**Severity:** CRITICAL

```python
self.imapclient = IMAPClient(self.host, ssl=True)
self.imapclient.login(self.username, self.password)
self.imapclient.select_folder('INBOX', readonly=False)
```

**Issue:** No exception handling for IMAP connection failures. If:
- Network is unavailable
- Credentials are invalid
- IMAP server is down
- SSL certificate issues occur

The application will crash with an unhandled exception. This is especially problematic for Gmail/Yahoo integration which may have OAuth flows, app-specific passwords, or different authentication requirements.

**Recommendation:** Wrap IMAP operations in try-except blocks catching `imapclient.IMAPClient.Error`, `socket.error`, `ssl.SSLError`. Implement connection retry logic. Validate credentials before attempting connection. Provide clear error messages for different failure modes.

---

### 3. No Environment Variable Validation

**File:** `src/ai.py`, `src/email_fetcher.py`, `src/main.py`  
**Lines:** Throughout  
**Severity:** CRITICAL

**Issue:** Environment variables are accessed with `os.getenv()` and `os.environ.get()` without validation:
- `src/ai.py:5-6`: `OPENAI_API_KEY`, `OPENAI_API_URL` can be `None`
- `src/ai.py:9-10`: `FOLDER_PREFIX` can be `None`, causing `AttributeError` in `startswith()`
- `src/email_fetcher.py:10-12`: IMAP credentials can be `None`
- `src/main.py:33,59,76`: Multiple uses of `os.getenv()` without defaults

This leads to cryptic errors like `AttributeError: 'NoneType' object has no attribute 'startswith'` instead of clear configuration errors.

**Recommendation:** Create a configuration validation module that:
- Checks all required environment variables at startup
- Provides clear error messages for missing/invalid values
- Validates URLs, email formats, and API key formats
- Uses pydantic or dataclasses for type-safe configuration

---

### 4. Type Safety: Complete Absence of Type Hints

**File:** All `src/*.py` files  
**Lines:** Throughout  
**Severity:** CRITICAL

**Issue:** Zero type hints in the entire codebase. This violates modern Python best practices and:
- Makes IDE support poor (no autocomplete, no type checking)
- Prevents static analysis with mypy/pyright
- Makes refactoring dangerous
- Creates ambiguity about function signatures
- Makes the codebase harder to maintain

**Recommendation:** Add comprehensive type hints to all functions using Python 3.10+ syntax (`str | None`, `list[str]`, etc.). Enable mypy in `pyproject.toml` and aim for strict mode compliance.

---

### 5. IMAP Move Operation Error Handling

**File:** `src/email_fetcher.py`  
**Lines:** 91-99  
**Severity:** HIGH

```python
def move_message(self, message_id, target_folder):
    try:
        self.imapclient.copy(message_id, target_folder)
        self.imapclient.delete_messages([message_id])
        self.imapclient.expunge()
    except Exception as e:
        print(f"An error occurred: {e}")
```

**Issue:** 
- Naked `Exception` catch
- Only prints error, doesn't raise or return status
- If `copy()` succeeds but `delete_messages()` fails, message is duplicated
- If `expunge()` fails, message is marked deleted but not removed
- No transaction-like rollback on partial failure

**Recommendation:** Catch specific IMAP exceptions. Implement proper error handling with status return. Consider using IMAP's `MOVE` command if server supports it (RFC 6851). Implement rollback logic: if delete fails, remove the copy.

---

### 6. OpenAI Client Usage Incompatible with Ollama

**File:** `src/ai.py`  
**Lines:** 43-71  
**Severity:** HIGH

**Issue:** The current OpenAI client usage has several problems for Ollama integration:

1. **Rate limit headers (lines 58-69):** Ollama's OpenAI-compatible API does not provide rate limit headers. This code will print `None` for all values and may cause errors if headers are missing.

2. **`with_raw_response` pattern (line 43):** This is specific to OpenAI's SDK. While Ollama's API is compatible, the raw response handling may differ.

3. **Model configuration (line 44):** Uses `os.environ.get("OPENAI_MODEL")` which may not match Ollama's model naming convention (e.g., `llama3:latest` vs `gpt-4-turbo`).

4. **No timeout configuration:** Ollama local models can be slow; no timeout is set, which could hang indefinitely.

**Recommendation:** 
- Abstract the AI client behind an interface/protocol
- Make rate limit header extraction optional (check if headers exist)
- Add configurable timeout parameters
- Support both OpenAI and Ollama model naming conventions
- Consider using the generic `httpx` or `requests` library for maximum compatibility

---

## Warnings

### 7. Duplicate Code: `remove_prefix` Function

**File:** `src/ai.py:8-11` and `src/util.py:7-10`  
**Severity:** WARNING

**Issue:** The `remove_prefix` function is duplicated in two files with identical implementation. This violates DRY principle and creates maintenance burden.

**Recommendation:** Remove from `src/ai.py` and import from `src/util.py`.

---

### 8. Unsafe Dictionary Access

**File:** `src/ai.py:73`  
**Severity:** WARNING

```python
message = response.choices[0].message.content
```

**Issue:** No validation that `response.choices` exists or has at least one element. If the API returns an empty choices list, this will raise `IndexError`.

**Recommendation:** Add validation: `if not response.choices: return ("invalid", "no choices in response")`

---

### 9. Email Parsing Assumes Structure

**File:** `src/email_fetcher.py:73`  
**Severity:** WARNING

```python
"from": f"{safe_decode(envelope.from_[0].mailbox)}@{safe_decode(envelope.from_[0].host)}",
```

**Issue:** Assumes `envelope.from_` exists and has at least one element. Assumes `mailbox` and `host` attributes exist. Will crash on emails with no sender or malformed addresses.

**Recommendation:** Add defensive checks: `if envelope.from_ and len(envelope.from_) > 0`. Handle cases where sender is missing or malformed.

---

### 10. No Logging Infrastructure

**File:** All files  
**Severity:** WARNING

**Issue:** All output uses `print()` statements instead of proper logging. This:
- Makes it impossible to control log levels
- Prevents logging to files
- Makes debugging production issues difficult
- Mixes user output with debug output

**Recommendation:** Implement Python's `logging` module with proper configuration. Use different log levels (DEBUG, INFO, WARNING, ERROR). Separate user-facing output from logs.

---

### 11. IMAP Flag Handling Inconsistent

**File:** `src/email_fetcher.py:89`  
**Severity:** WARNING

```python
def set_unseen(self, message_id):
    self.imapclient.remove_flags(message_id, [b'\\Seen'])
```

**Issue:** Hardcodes the flag as bytes `b'\\Seen'` but other methods use strings. Inconsistent types. The backslash escaping may not be correct for all IMAP servers.

**Recommendation:** Use IMAPClient's constants or string representation consistently. Test with different IMAP servers (Gmail, Yahoo) to ensure flag handling works.

---

### 12. No IMAP Provider-Specific Configuration

**File:** `src/email_fetcher.py` and `.env.dist`  
**Severity:** WARNING

**Issue:** Current implementation assumes a generic IMAP host. For Gmail and Yahoo integration, provider-specific settings are needed:
- Gmail: `imap.gmail.com`, port 993, requires app-specific passwords or OAuth
- Yahoo: `imap.mail.yahoo.com`, port 993, requires app-specific passwords
- Different authentication mechanisms (OAuth2 vs plain auth)
- Different folder structures and flag behaviors

**Recommendation:** Add provider configuration class that encapsulates host, port, auth method, and provider-specific quirks. Extend `.env.dist` with provider-specific settings.

---

### 13. Missing Dependencies in pyproject.toml

**File:** `pyproject.toml`  
**Severity:** WARNING

**Issue:** The project lists `numpy`, `pandas`, and `scikit-learn` as dependencies but they are not used in the codebase. This bloats the installation and creates security surface area.

**Recommendation:** Remove unused dependencies. Add `httpx` or `requests` for better HTTP client control. Add `pydantic` for configuration validation. Add `mypy` for type checking.

---

### 14. No Test Coverage

**File:** `tests/` directory  
**Severity:** WARNING

**Issue:** The `tests/` directory exists but contains only an empty `__init__.py` file. Zero test coverage for:
- Email parsing logic
- AI prompt generation
- Folder name handling
- IMAP operations
- API client interactions

**Recommendation:** Implement comprehensive test suite using `pytest`. Mock IMAP and OpenAI/Ollama connections. Test edge cases (malformed emails, API failures, network timeouts). Aim for >80% coverage.

---

## Info-Level Issues

### 15. Import Ordering

**File:** `src/main.py`  
**Severity:** INFO

**Issue:** Imports are not grouped according to PEP 8 (stdlib, third-party, local). Missing newline between groups.

**Recommendation:** Run `isort` on all files to standardize import ordering.

---

### 16. Magic Numbers and Strings

**File:** `src/util.py:15`  
**Severity:** INFO

```python
def limit_consecutive_linefeeds(text, max_linefeeds=2):
```

**Issue:** Default value of `2` is a magic number. No explanation of why this value was chosen.

**Recommendation:** Add docstring explaining the rationale. Consider making it configurable.

---

### 17. No Docstrings

**File:** All functions  
**Severity:** INFO

**Issue:** Functions lack docstrings. This makes the codebase harder to understand and maintain.

**Recommendation:** Add Google-style or NumPy-style docstrings to all public functions and classes.

---

### 18. Signal Handler Incomplete

**File:** `src/util.py:35-37`  
**Severity:** INFO

```python
def signal_handler(signal, frame):
    print("\nExiting...")
    sys.exit(0)
```

**Issue:** Signal handler doesn't clean up resources (IMAP connection, file handles). Could leave connections in bad state.

**Recommendation:** Add cleanup logic or make signal handler set a flag that main loop checks for graceful shutdown.

---

## Ollama Integration Specific Recommendations

### Current OpenAI Client Usage Analysis

The current implementation in `src/ai.py` uses the OpenAI Python SDK v1.26.0 with the following pattern:

1. **Configuration (lines 4-6):** Sets `api_key` and `base_url` globally on the `openai` module
2. **API Call (lines 43-55):** Uses `chat.completions.with_raw_response.create()` 
3. **Response Parsing (lines 57-71):** Extracts rate limit headers, then parses response
4. **Content Extraction (line 73):** Gets `choices[0].message.content`

### Required Changes for Ollama

1. **Remove Rate Limit Header Dependencies:** Ollama does not provide rate limit headers. Wrap header extraction in conditional checks or make it optional based on provider.

2. **Add Timeout Configuration:** Ollama local models can be slow. Add `timeout` parameter to API calls:
   ```python
   response = openai.chat.completions.create(
       ...,
       timeout=float(os.getenv("AI_TIMEOUT", "30.0"))
   )
   ```

3. **Model Name Mapping:** Ollama uses different model naming (e.g., `llama3:latest`, `mistral:7b`). Add model name validation and mapping logic.

4. **Base URL Configuration:** The `.env.dist` already shows Ollama URL pattern (`http://localhost:11434/v1/`), but the code needs to handle:
   - HTTP vs HTTPS (Ollama defaults to HTTP)
   - Different port configurations
   - Containerized Ollama instances

5. **Streaming Support:** Consider adding streaming support for better UX with slower local models.

6. **Fallback Logic:** Implement fallback from Ollama to OpenAI if Ollama is unavailable, or vice versa.

### Recommended Architecture

Create an abstraction layer:

```python
from abc import ABC, abstractmethod
from typing import Tuple

class AIProvider(ABC):
    @abstractmethod
    def classify_email(self, message: dict, folders: list[str]) -> Tuple[str, str]:
        pass

class OpenAIProvider(AIProvider):
    # OpenAI-specific implementation
    pass

class OllamaProvider(AIProvider):
    # Ollama-specific implementation
    pass
```

This allows easy switching between providers and isolates provider-specific logic.

---

## IMAP Provider Integration Recommendations

### Current IMAP Implementation Analysis

The current `EmailFetcher` class in `src/email_fetcher.py`:

1. **Hardcoded host (line 10):** Reads from `IMAP_HOST` environment variable
2. **SSL always on (line 15):** Assumes SSL/TLS
3. **Generic login (line 16):** Uses username/password
4. **INBOX only (line 17):** Hardcodes INBOX folder
5. **Generic flag handling (lines 20, 25, 68, 89):** Uses custom 'SortBuddy' flag

### Required Changes for Gmail/Yahoo

1. **Provider Configuration:** Create provider-specific configuration:

```python
@dataclass
class IMAPProvider:
    name: str
    host: str
    port: int
    ssl: bool
    auth_method: str  # "plain", "oauth2", "app_password"
    folder_prefix: str = ""
    
GMAIL = IMAPProvider("gmail", "imap.gmail.com", 993, True, "oauth2")
YAHOO = IMAPProvider("yahoo", "imap.mail.yahoo.com", 993, True, "app_password")
GENERIC = IMAPProvider("generic", "", 993, True, "plain")
```

2. **OAuth2 Support for Gmail:** Gmail requires OAuth2 for new accounts. Need to:
   - Add OAuth2 dependency (`google-auth-oauthlib`, `google-api-python-client`)
   - Implement OAuth2 flow
   - Store tokens securely
   - Handle token refresh

3. **App-Specific Passwords:** Yahoo and some Gmail accounts require app-specific passwords. Add UI/documentation for generating these.

4. **Folder Structure Differences:** 
   - Gmail uses labels (not traditional folders)
   - Yahoo has different folder naming conventions
   - Need to map provider-specific folders to generic structure

5. **Connection Pooling:** For multiple accounts, implement connection pooling to avoid opening/closing connections repeatedly.

6. **Idle Support:** Consider adding IMAP IDLE support for real-time email processing.

### Error Handling Improvements

1. **Authentication Failures:** Distinguish between:
   - Invalid credentials
   - Account locked
   - OAuth token expired
   - App password required

2. **Network Failures:** Implement retry with exponential backoff for:
   - Connection timeouts
   - DNS failures
   - SSL handshake failures

3. **Quota Exceeded:** Handle storage quota errors from providers.

4. **Rate Limiting:** Implement rate limiting for API calls to avoid provider blocking.

---

## Maintainability Concerns

### 1. Tight Coupling

The code has tight coupling between:
- AI client and configuration
- IMAP client and folder structure
- Main loop and email processing logic

**Recommendation:** Implement dependency injection and interfaces to decouple components.

### 2. No Configuration Management

Configuration is scattered across:
- Environment variables
- Hardcoded values
- Command-line arguments

**Recommendation:** Centralize configuration using a configuration class with validation.

### 3. No State Management

The application has no concept of state:
- No tracking of processed emails
- No resume capability after interruption
- No audit trail

**Recommendation:** Add state persistence (SQLite or JSON) to track processed emails and enable resume.

### 4. No Monitoring/Observability

No metrics or monitoring:
- No success/failure counts
- No timing information
- No error tracking

**Recommendation:** Add basic metrics collection (success rate, processing time, error counts).

---

## Type Safety Implementation Plan

### Immediate Actions

1. **Add type hints to all functions:**
   ```python
   def remove_prefix(folder_name: str) -> str:
       prefix = os.environ.get("FOLDER_PREFIX", "")
       if folder_name.startswith(prefix):
           return folder_name[len(prefix):]
       return folder_name
   ```

2. **Enable mypy in pyproject.toml:**
   ```toml
   [tool.mypy]
   python_version = "3.10"
   warn_return_any = true
   warn_unused_configs = true
   disallow_untyped_defs = true
   ```

3. **Add pydantic for configuration:**
   ```python
   from pydantic import BaseModel, Field, validator
   
   class Config(BaseModel):
       openai_api_key: str = Field(..., env="OPENAI_API_KEY")
       openai_api_url: str = Field(..., env="OPENAI_API_URL")
       openai_model: str = Field(..., env="OPENAI_MODEL")
       folder_prefix: str = Field(default="AI-", env="FOLDER_PREFIX")
       
       @validator('openai_api_url')
       def validate_url(cls, v):
           if not v.startswith(('http://', 'https://')):
               raise ValueError('URL must start with http:// or https://')
           return v
   ```

### Long-term Actions

1. **Aim for mypy strict mode compliance**
2. **Add pre-commit hooks for type checking**
3. **Use type stubs for external libraries if needed**

---

## Testing Strategy Recommendations

### Unit Tests Needed

1. **AI Module:**
   - Test prompt generation with various email formats
   - Test folder name stripping logic
   - Test response parsing with valid/invalid formats
   - Mock OpenAI/Ollama API calls

2. **Email Fetcher Module:**
   - Test email parsing with multipart messages
   - Test HTML to text conversion
   - Test folder listing
   - Test flag operations
   - Mock IMAPClient

3. **Util Module:**
   - Test string manipulation functions
   - Test encoding/decoding
   - Test JSON serialization

### Integration Tests Needed

1. **End-to-end with mock IMAP server**
2. **End-to-end with mock AI server**
3. **Configuration validation tests**
4. **Error recovery tests**

### Test Infrastructure

1. **Add pytest to dependencies**
2. **Add pytest-mock for mocking**
3. **Add pytest-cov for coverage**
4. **Create fixtures for common test data**

---

## Specific Recommendations for Implementation Phase

### Phase 1: Foundation (Before Ollama/IMAP)

1. **Add type hints to all existing code**
2. **Implement proper logging infrastructure**
3. **Add configuration validation with pydantic**
4. **Remove duplicate code**
5. **Add basic error handling (no more naked exceptions)**
6. **Set up test infrastructure**
7. **Add unit tests for existing logic**

### Phase 2: AI Provider Abstraction

1. **Create AIProvider interface/protocol**
2. **Implement OpenAIProvider class**
3. **Implement OllamaProvider class**
4. **Add provider selection logic**
5. **Add timeout and retry configuration**
6. **Make rate limit header extraction optional**
7. **Add tests for both providers**

### Phase 3: IMAP Provider Abstraction

1. **Create IMAPProvider configuration class**
2. **Add provider-specific settings (Gmail, Yahoo, Generic)**
3. **Implement OAuth2 flow for Gmail**
4. **Add app-specific password handling**
5. **Improve error handling for IMAP operations**
6. **Add connection retry logic**
7. **Add tests for each provider**

### Phase 4: Integration and Testing

1. **Integrate new abstractions into main.py**
2. **Add end-to-end tests**
3. **Add state persistence**
4. **Add monitoring/metrics**
5. **Update documentation**
6. **Test with real Gmail and Yahoo accounts**

---

## PASS/FAIL Verdict

**FAIL**

The codebase requires significant refactoring before Ollama and IMAP provider integration can be safely implemented. Critical issues (naked exceptions, no type hints, no error handling, no tests) must be addressed first. The current architecture is not sufficiently robust to support the planned enhancements without introducing significant technical debt and risk.

---

## Priority Action Items

1. **CRITICAL:** Add type hints to all functions
2. **CRITICAL:** Replace naked `Exception` catches with specific exceptions
3. **CRITICAL:** Add environment variable validation at startup
4. **CRITICAL:** Add IMAP connection error handling
5. **HIGH:** Create AI provider abstraction layer
6. **HIGH:** Create IMAP provider configuration system
7. **HIGH:** Implement proper logging infrastructure
8. **HIGH:** Add basic unit test coverage
9. **MEDIUM:** Remove duplicate code
10. **MEDIUM:** Add configuration validation with pydantic

---

## Conclusion

The Sort Buddy codebase is functionally simple but structurally fragile. The planned Ollama and IMAP provider integrations will significantly increase complexity, and the current code is not prepared to handle this complexity. A refactoring phase focused on type safety, error handling, and abstraction is essential before implementing the new features. The recommendations in this review provide a clear path forward for creating a robust, maintainable codebase that can support the planned enhancements.
