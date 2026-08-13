# Ollama + IMAP Provider Integration Implementation Plan

**Date:** 2026-08-12
**Planner:** planner agent
**Coordinator:** coordinator agent
**Branch:** feature/ollama-imap-integration

## Executive Summary

Sort Buddy is an AI-powered email classifier that currently supports OpenAI via its API and generic IMAP email servers. This plan details the implementation of two major enhancements:

1. **Ollama Integration:** Enable Sort Buddy to use local Ollama models via their OpenAI-compatible API endpoint, providing a cost-effective alternative to OpenAI.
2. **Multi-Provider IMAP Support:** Add specific support for Gmail and Yahoo Mail in addition to the existing generic IMAP provider, including provider-specific authentication (app passwords) and configuration.

The implementation follows a phased approach with parallelizable work streams, comprehensive testing, and security considerations integrated throughout. The architecture reviews identified several critical issues (no type hints, naked exception handling, no configuration validation) that will be addressed as foundational work before adding new features.

## Goals and Non-Goals

### Goals
- Enable Sort Buddy to use Ollama's OpenAI-compatible `/v1/chat/completions` endpoint as an alternative to OpenAI
- Add provider-specific IMAP support for Gmail and Yahoo Mail with appropriate authentication
- Implement configuration-driven provider selection (AI provider and email provider)
- Maintain backward compatibility with existing OpenAI and generic IMAP configurations
- Add comprehensive test coverage for new functionality
- Improve code quality (type hints, error handling, configuration validation)
- Document the new configuration options and provider-specific requirements

### Non-Goals
- OAuth2 authentication for Gmail/Yahoo (deferred to future work; will use app passwords)
- IMAP IDLE support for real-time email processing
- Web UI or API endpoints
- Multi-account support
- OAuth2 token refresh and management
- Streaming responses from AI providers
- Custom Ollama-native endpoints (only OpenAI-compatible endpoint)

## Current State Assessment

Based on five specialist reviews (architecture, Python, security, Ollama, testing), the current codebase has:

**Strengths:**
- Functional architecture with clear separation between AI, email fetching, and orchestration
- Proper use of environment variables for credentials
- SSL/TLS enabled for IMAP connections
- BeautifulSoup for HTML sanitization
- JSON mock fetcher for testing/benchmarking

**Critical Issues to Address:**
- No type hints anywhere in the codebase (security: CRITICAL)
- Naked exception handling with `exit()` calls (security: CRITICAL, testing: CRITICAL)
- No environment variable validation (security: CRITICAL, Python: CRITICAL)
- IMAP connection in `__init__` makes unit testing difficult (testing: HIGH)
- No test coverage (testing: FAIL - zero tests)
- Duplicate utility functions in `ai.py` and `util.py` (architecture: WARNING)
- No configuration management (architecture: CRITICAL)
- Tight coupling to OpenAI-specific patterns (architecture: CRITICAL)
- No abstraction for email providers (architecture: CRITICAL)

**Ollama-Specific Findings:**
- Current code can technically hit Ollama endpoint but lacks proper error handling
- No timeout configuration (Ollama cold starts can be slow)
- Rate limit header parsing will fail with Ollama (no headers provided)
- Module-level `openai.api_key`/`base_url` makes testing difficult
- Response parsing is brittle (single `: ` delimiter)

**IMAP Provider Findings:**
- Generic IMAP only; no provider-specific logic
- No support for Gmail labels or Yahoo folder quirks
- Authentication limited to username/password (no app password support)
- No connection retry logic or timeout configuration
- IMAP move operation has partial failure risk

## Proposed Architecture

### File/Directory Structure Changes

```
sort-buddy/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Controller (refactored)
│   ├── config.py                  # NEW: Configuration management with Pydantic
│   ├── models/                    # NEW: Data models
│   │   ├── __init__.py
│   │   ├── email.py               # Email message model
│   │   └── classification.py      # Classification result model
│   ├── ai/                        # NEW: AI service layer
│   │   ├── __init__.py
│   │   ├── base.py                # AI client interface
│   │   ├── openai_client.py       # OpenAI implementation
│   │   ├── ollama_client.py       # Ollama implementation
│   │   ├── factory.py             # Client factory
│   │   └── prompts.py             # Prompt templates
│   ├── email/                     # NEW: Email service layer
│   │   ├── __init__.py
│   │   ├── base.py                # Email provider interface
│   │   ├── generic_imap.py        # Generic IMAP implementation
│   │   ├── gmail_provider.py      # Gmail implementation
│   │   ├── yahoo_provider.py      # Yahoo implementation
│   │   ├── factory.py             # Provider factory
│   │   └── parsers.py             # Email parsing logic
│   └── util.py                    # Utilities (refactored, remove duplicates)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # NEW: Shared fixtures
│   ├── fixtures/                  # NEW: Test data
│   │   ├── emails/
│   │   └── responses/
│   ├── unit/                      # NEW: Unit tests
│   │   ├── test_config.py
│   │   ├── test_ai/
│   │   ├── test_email/
│   │   ├── test_models/
│   │   └── test_util.py
│   └── integration/               # NEW: Integration tests (optional, local only)
├── .env.dist                      # UPDATED: New provider variables
├── pyproject.toml                 # UPDATED: New dependencies
└── README.md                      # UPDATED: New documentation
```

### Key Abstractions

**AI Client Interface (`src/ai/base.py`):**
```python
class AIClient(ABC):
    @abstractmethod
    def configure(self, config: LLMConfig) -> None: pass
    
    @abstractmethod
    def classify_email(self, message: dict, folders: list[str], 
                      show_prompt: bool, show_rate_limits: bool) -> Tuple[str, str]: pass
    
    @abstractmethod
    def health_check(self) -> bool: pass
```

**Email Provider Interface (`src/email/base.py`):**
```python
class EmailProvider(ABC):
    @abstractmethod
    def connect(self, dry_run: bool = False) -> None: pass
    
    @abstractmethod
    def list_ai_folders(self, prefix: str) -> List[str]: pass
    
    @abstractmethod
    def fetch_next_message(self) -> Optional[Dict]: pass
    
    @abstractmethod
    def move_message(self, message_id: str, target_folder: str) -> bool: pass
    
    @abstractmethod
    def has_more_messages(self) -> bool: pass
    
    @abstractmethod
    def close(self) -> None: pass
```

**Configuration Model (`src/config.py`):**
```python
class AppConfig(BaseModel):
    llm_provider: str = "openai"
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout: float = 60.0
    
    email_provider: str = "generic"
    imap_host: Optional[str] = None
    imap_port: int = 993
    imap_use_ssl: bool = True
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    
    gmail_username: Optional[str] = None
    gmail_app_password: Optional[str] = None
    
    yahoo_username: Optional[str] = None
    yahoo_app_password: Optional[str] = None
    
    folder_prefix: str = "AI-"
```

## Ollama/OpenAI API Integration Plan

### Configuration Approach

**Provider Selection via Environment Variables:**
```bash
# AI Provider Selection
LLM_PROVIDER="openai"  # or "ollama"

# OpenAI Configuration (when LLM_PROVIDER=openai)
OPENAI_API_KEY="[your-openai-api-key]"
OPENAI_API_URL="https://api.openai.com/v1/"
OPENAI_MODEL="gpt-4-turbo"

# Ollama Configuration (when LLM_PROVIDER=ollama)
OLLAMA_BASE_URL="http://localhost:11434/v1/"
OLLAMA_MODEL="llama3.1:latest"
OLLAMA_TIMEOUT=60.0

# Backward compatibility: map OPENAI_* to LLM_* when provider is openai
```

**Backward Compatibility Strategy:**
- If `LLM_PROVIDER` is not set, infer from `OPENAI_API_URL` (default to "openai")
- Map legacy `OPENAI_API_URL` → `LLM_BASE_URL`, `OPENAI_API_KEY` → `LLM_API_KEY`, `OPENAI_MODEL` → `LLM_MODEL`
- This allows existing `.env` files to work without changes

### Implementation Details

**Client Factory Pattern:**
```python
def create_ai_client(config: AppConfig) -> AIClient:
    if config.llm_provider == "openai":
        client = OpenAIClient()
    elif config.llm_provider == "ollama":
        client = OllamaClient()
    else:
        raise ValueError(f"Unknown AI provider: {config.llm_provider}")
    
    client.configure(config)
    return client
```

**Ollama-Specific Considerations:**
1. **Timeout:** Default to 60 seconds (configurable via `OLLAMA_TIMEOUT`)
2. **API Key:** Use placeholder "ollama" for local instances
3. **Rate Limits:** Skip rate limit header printing for Ollama (headers not provided)
4. **Model Validation:** Check if model exists via `/api/tags` or handle 404 gracefully
5. **Error Handling:** Catch `openai.APIConnectionError` (Ollama not running), `openai.NotFoundError` (model not found)
6. **Response Parsing:** Make delimiter parsing more robust (handle extra whitespace)

**OpenAI-Specific Considerations:**
1. **Rate Limits:** Continue reading and printing `x-ratelimit-*` headers
2. **Timeout:** Use shorter default (30 seconds) for cloud API
3. **Error Handling:** Catch `openai.RateLimitError`, `openai.APITimeoutError`, `openai.APIError`

### Code Changes

**New Files:**
- `src/ai/base.py` - Abstract interface
- `src/ai/openai_client.py` - OpenAI implementation (migrated from `ai.py`)
- `src/ai/ollama_client.py` - Ollama implementation
- `src/ai/factory.py` - Client factory
- `src/ai/prompts.py` - Prompt templates (extracted from string concatenation)
- `src/config.py` - Configuration management

**Modified Files:**
- `src/ai.py` - Deprecated, keep as thin compatibility wrapper
- `src/main.py` - Use factory instead of direct `configure_openai()`
- `.env.dist` - Add Ollama variables

**Deleted Code:**
- Duplicate `remove_prefix()` and `get_stripped_folder_list()` from `ai.py`

## IMAP Provider Integration Plan

### Configuration Approach

**Provider Selection via Environment Variables:**
```bash
# Email Provider Selection
EMAIL_PROVIDER="generic"  # or "gmail", "yahoo"

# Generic IMAP Configuration (when EMAIL_PROVIDER=generic)
IMAP_HOST="[imap.somehost.com]"
IMAP_PORT=993
IMAP_USE_SSL=true
EMAIL_USERNAME="[your email]"
EMAIL_PASSWORD="[your password]"

# Gmail Configuration (when EMAIL_PROVIDER=gmail)
GMAIL_USERNAME="[your@gmail.com]"
GMAIL_APP_PASSWORD="[your app password]"
GMAIL_LABEL_PREFIX="AI-"

# Yahoo Configuration (when EMAIL_PROVIDER=yahoo)
YAHOO_USERNAME="[your@yahoo.com]"
YAHOO_APP_PASSWORD="[your app password]"
YAHOO_FOLDER_PREFIX="AI-"

# Common
FOLDER_PREFIX="AI-"
```

**Backward Compatibility Strategy:**
- If `EMAIL_PROVIDER` is not set, default to "generic"
- Use existing `IMAP_HOST`, `EMAIL_USERNAME`, `EMAIL_PASSWORD` for generic provider
- This allows existing `.env` files to work without changes

### Provider-Specific Implementations

**Generic IMAP Provider (`src/email/generic_imap.py`):**
- Refactor existing `email_fetcher.py` logic
- Add connection retry logic with exponential backoff
- Add timeout configuration
- Improve error handling for connection failures
- Separate configuration from connection (for testability)

**Gmail Provider (`src/email/gmail_provider.py`):**
- Host: `imap.gmail.com`, Port: 993, SSL: True
- Authentication: App-specific passwords (document OAuth2 as future work)
- Handle Gmail labels (which map to IMAP folders)
- Use Gmail-specific search syntax if needed
- Handle Gmail's threading model (basic support)

**Yahoo Provider (`src/email/yahoo_provider.py`):**
- Host: `imap.mail.yahoo.com`, Port: 993, SSL: True
- Authentication: App-specific passwords
- Handle Yahoo folder structure and delimiter
- Handle Yahoo-specific IMAP quirks

**Provider Factory:**
```python
def create_email_provider(config: AppConfig, dry_run: bool = False) -> EmailProvider:
    if config.email_provider == "gmail":
        provider = GmailProvider()
        provider.configure(config)
    elif config.email_provider == "yahoo":
        provider = YahooProvider()
        provider.configure(config)
    else:  # generic
        provider = GenericIMAPProvider()
        provider.configure(config)
    
    provider.connect(dry_run=dry_run)
    return provider
```

### Code Changes

**New Files:**
- `src/email/base.py` - Abstract interface
- `src/email/generic_imap.py` - Generic IMAP implementation (migrated from `email_fetcher.py`)
- `src/email/gmail_provider.py` - Gmail implementation
- `src/email/yahoo_provider.py` - Yahoo implementation
- `src/email/factory.py` - Provider factory
- `src/email/parsers.py` - Email parsing logic (extracted from fetcher)

**Modified Files:**
- `src/email_fetcher.py` - Deprecated, keep as thin compatibility wrapper
- `src/main.py` - Use factory instead of direct `EmailFetcher` instantiation
- `.env.dist` - Add Gmail/Yahoo variables

**Deleted Code:**
- None (keep `email_fetcher.py` as compatibility wrapper)

## Configuration & Environment Variables

### New Environment Variables

**AI Provider Variables:**
```bash
LLM_PROVIDER="openai"              # "openai" or "ollama"
LLM_BASE_URL="https://api.openai.com/v1/"  # Provider endpoint
LLM_API_KEY="[api-key]"             # API key or placeholder
LLM_MODEL="gpt-4-turbo"             # Model name
LLM_TIMEOUT=60.0                    # Request timeout in seconds
```

**Email Provider Variables:**
```bash
EMAIL_PROVIDER="generic"           # "generic", "gmail", or "yahoo"
IMAP_HOST="[imap.host.com]"         # Generic IMAP host
IMAP_PORT=993                       # IMAP port
IMAP_USE_SSL=true                   # Use SSL/TLS
EMAIL_USERNAME="[user@example.com]" # Generic email username
EMAIL_PASSWORD="[password]"         # Generic email password
GMAIL_USERNAME="[user@gmail.com]"  # Gmail username
GMAIL_APP_PASSWORD="[app-pw]"      # Gmail app password
YAHOO_USERNAME="[user@yahoo.com]"  # Yahoo username
YAHOO_APP_PASSWORD="[app-pw]"      # Yahoo app password
```

**Backward Compatibility Variables (mapped internally):**
```bash
OPENAI_API_KEY → LLM_API_KEY (when LLM_PROVIDER=openai)
OPENAI_API_URL → LLM_BASE_URL (when LLM_PROVIDER=openai)
OPENAI_MODEL → LLM_MODEL (when LLM_PROVIDER=openai)
IMAP_HOST → IMAP_HOST (when EMAIL_PROVIDER=generic)
EMAIL_USERNAME → EMAIL_USERNAME (when EMAIL_PROVIDER=generic)
EMAIL_PASSWORD → EMAIL_PASSWORD (when EMAIL_PROVIDER=generic)
```

### .env.dist Changes

The `.env.dist` file will be updated to include:
1. New `LLM_*` variables with clear comments
2. New `EMAIL_PROVIDER` variable
3. New `GMAIL_*` variables with comments about app passwords
4. New `YAHOO_*` variables with comments about app passwords
5. Documentation for backward compatibility mapping
6. Clear examples for each provider combination

## Dependency and pyproject.toml Changes

### New Dependencies

**Required:**
```toml
pydantic = "^2.0.0"           # Configuration validation
pydantic-settings = "^2.0.0"   # Environment variable loading
pytest = "^7.0.0"              # Test framework
pytest-mock = "^3.10.0"        # Mocking support
pytest-cov = "^4.0.0"          # Coverage reporting
pytest-socket = "^0.6.0"       # Disable network in tests
mypy = "^1.0.0"                # Type checking
```

**Optional (for future OAuth2):**
```toml
# google-auth-oauthlib = "^1.0.0"  # Deferred
# google-api-python-client = "^2.0.0"  # Deferred
```

### Dependencies to Remove

**Unused (identified in reviews):**
```toml
# numpy = "^1.26.4"  # Not used in code
# pandas = "^2.2.2"  # Not used in code
# scikit-learn = "^1.4.2"  # Not used in code
# mail-parser = "^3.15.0"  # Not used in code (custom parsing)
```

**Updated pyproject.toml structure:**
```toml
[tool.poetry.dependencies]
python = "^3.10"
openai = "^1.26.0"
python-dotenv = "^1.0.1"
imapclient = "^3.0.1"
beautifulsoup4 = "^4.12.3"
lxml = "^5.2.1"
colorama = "^0.4.6"
pydantic = "^2.0.0"
pydantic-settings = "^2.0.0"

[tool.poetry.group.test.dependencies]
pytest = "^7.0.0"
pytest-mock = "^3.10.0"
pytest-cov = "^4.0.0"
pytest-socket = "^0.6.0"

[tool.poetry.group.dev.dependencies]
mypy = "^1.0.0"
```

### mypy Configuration

Add to `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
strict = true
```

## Testing Strategy

### Test Infrastructure

**Framework:** pytest with pytest-mock, pytest-cov, pytest-socket

**Coverage Target:** 80% minimum for modified modules (`src/ai/`, `src/email/`, `src/config.py`, `src/main.py`)

**Test Structure:**
```
tests/
├── conftest.py                    # Shared fixtures
├── fixtures/
│   ├── emails/                    # Sample email files (.eml)
│   │   ├── plain_text.eml
│   │   ├── html_only.eml
│   │   └── multipart.eml
│   └── responses/                 # Mock API responses
│       ├── openai_valid.json
│       ├── ollama_valid.json
│       └── invalid_no_colon.json
├── unit/
│   ├── test_config.py
│   ├── test_ai/
│   │   ├── test_openai_client.py
│   │   ├── test_ollama_client.py
│   │   ├── test_factory.py
│   │   └── test_prompts.py
│   ├── test_email/
│   │   ├── test_generic_imap.py
│   │   ├── test_gmail_provider.py
│   │   ├── test_yahoo_provider.py
│   │   ├── test_factory.py
│   │   └── test_parsers.py
│   ├── test_models/
│   │   ├── test_email.py
│   │   └── test_classification.py
│   └── test_util.py
└── integration/                   # Optional, local only
    ├── test_ollama_integration.py
    └── test_imap_integration.py
```

### Mocking Strategy

**IMAP Mocking:**
- Patch `imapclient.IMAPClient` at module level
- Use realistic fixture data for folder listings and email content
- Never connect to real IMAP servers in unit tests
- Test with `--disable-socket` flag

**OpenAI/Ollama Mocking:**
- Patch `openai.chat.completions.with_raw_response.create`
- Return fake response objects with appropriate headers
- Parameterize tests for both providers
- Test rate limit header presence/absence

**Environment Mocking:**
- Use `monkeypatch.setenv` for all environment variables
- Never rely on real `.env` file in tests
- Test configuration validation with missing/invalid values

### Test Waves

**Wave 0: Bootstrap Tooling**
- Add test dependencies
- Create `conftest.py` with shared fixtures
- Configure pytest with coverage and socket blocking

**Wave 1: Back-fill Existing Code Tests**
- Test utility functions (pure functions first)
- Test existing AI module (before refactoring)
- Test existing email fetcher (before refactoring)
- Test main.py orchestration

**Wave 2: Test New AI Layer**
- Test AI client interface
- Test OpenAI client implementation
- Test Ollama client implementation
- Test client factory
- Test prompt templates

**Wave 3: Test New Email Layer**
- Test email provider interface
- Test generic IMAP provider
- Test Gmail provider
- Test Yahoo provider
- Test provider factory
- Test email parsers

**Wave 4: Test Configuration**
- Test configuration loading
- Test configuration validation
- Test provider selection logic
- Test backward compatibility mapping

**Wave 5: Integration Tests (Optional)**
- Test with real Ollama instance (local only, skipped in CI)
- Test with real IMAP server (local only, skipped in CI)
- Document how to run locally

### CI/CD Integration

**GitHub Actions Step:**
```yaml
- name: Run tests
  run: poetry run pytest --cov=src --cov-report=xml --cov-fail-under=80 --disable-socket
```

**Pre-commit Hooks:**
- mypy type checking
- pytest with coverage
- isort for import ordering

## Security Considerations

### Credential Handling

**Current State:** ✅ Good - credentials in environment variables, `.env` in `.gitignore`

**Enhancements:**
1. Add configuration validation to ensure required credentials are present
2. Sanitize error messages to prevent secret leakage
3. Add warning when `--show-prompt` displays email content
4. Add file permission restrictions (0600) for JSON output

### Ollama Security

**Recommendations:**
1. Document that Ollama should bind to `127.0.0.1:11434` for local-only access
2. Recommend HTTPS for remote Ollama instances
3. Document Ollama authentication if network-accessible
4. Add conditional API key setting (skip for localhost HTTP)

### IMAP Security

**Enhancements:**
1. Explicit SSL context configuration (prevent MITM)
2. Add IMAP host validation (hostname/IP format)
3. Implement transaction-like behavior for move operations (copy → verify → delete)
4. Add rate limiting to avoid provider blocking
5. Document app password requirements for Gmail/Yahoo

### Input Validation

**Enhancements:**
1. Add content length validation for email bodies
2. Validate CLI argument ranges (e.g., `--limit`)
3. Add path validation for `--save-to-json` and `--use-json`
4. Prevent directory traversal via path arguments

### Error Handling

**Critical Fix:** Replace `exit()` calls with raised exceptions
- This prevents abrupt termination and allows proper cleanup
- Enables testing of error paths
- Provides better error messages

## Implementation Waves

### Wave 1: Foundation (Foundation Refactor)
**Goal:** Address critical issues before adding new features
**Parallelizable:** Yes (subtasks can run in parallel)

**Subtasks:**
1. Add type hints to all existing code
2. Implement logging infrastructure (replace `print()`)
3. Add configuration validation with Pydantic
4. Remove duplicate code (`remove_prefix`, `get_stripped_folder_list`)
5. Replace `exit()` calls with raised exceptions
6. Add test infrastructure (pytest, fixtures)
7. Add unit tests for existing code

**Owner:** python-developer, testing-guardian
**Risk:** Medium (refactoring existing code)
**Estimated Time:** 2-3 days

### Wave 2: AI Layer Abstraction (Ollama Integration)
**Goal:** Implement AI client abstraction with Ollama support
**Parallelizable:** Yes (OpenAI and Ollama clients can be developed in parallel)

**Subtasks:**
1. Create AI client interface (`src/ai/base.py`)
2. Migrate OpenAI logic to `src/ai/openai_client.py`
3. Implement Ollama client (`src/ai/ollama_client.py`)
4. Create AI client factory (`src/ai/factory.py`)
5. Extract prompt templates (`src/ai/prompts.py`)
6. Update `main.py` to use factory
7. Add tests for AI layer
8. Update `.env.dist` with Ollama variables

**Owner:** ollama-specialist, python-developer, testing-guardian
**Risk:** Medium (new abstraction layer)
**Estimated Time:** 2-3 days

### Wave 3: Email Layer Abstraction (IMAP Provider Support)
**Goal:** Implement email provider abstraction with Gmail/Yahoo support
**Parallelizable:** Yes (providers can be developed in parallel)

**Subtasks:**
1. Create email provider interface (`src/email/base.py`)
2. Migrate generic IMAP logic to `src/email/generic_imap.py`
3. Implement Gmail provider (`src/email/gmail_provider.py`)
4. Implement Yahoo provider (`src/email/yahoo_provider.py`)
5. Create email provider factory (`src/email/factory.py`)
6. Extract email parsing logic (`src/email/parsers.py`)
7. Update `main.py` to use factory
8. Add tests for email layer
9. Update `.env.dist` with Gmail/Yahoo variables

**Owner:** python-developer, testing-guardian
**Risk:** Medium (new abstraction layer)
**Estimated Time:** 3-4 days

### Wave 4: Integration and Documentation
**Goal:** Integrate changes, update documentation, and verify end-to-end

**Subtasks:**
1. Update `README.md` with new configuration options
2. Add provider-specific setup instructions
3. Update `run.sh` if needed
4. End-to-end testing with both providers
5. Security review of new code
6. Python code review
7. Finalize backward compatibility testing

**Owner:** documentation-agent, security-auditor, python-reviewer
**Risk:** Low (documentation and verification)
**Estimated Time:** 1-2 days

### Wave 5: Verification and Release
**Goal:** Final verification, CI setup, and release preparation

**Subtasks:**
1. Run full test suite with coverage
2. mypy strict mode compliance check
3. Security audit
4. Integration testing (optional, local)
5. Prepare release notes
6. Create git commit
7. Coordinate merge to main

**Owner:** qa-ci-agent, security-auditor, python-reviewer, git-workflow
**Risk:** Low (verification only)
**Estimated Time:** 1 day

## Acceptance Criteria

### Overall Acceptance Criteria

1. **Functional Requirements:**
   - [ ] Sort Buddy can use Ollama via OpenAI-compatible API
   - [ ] Sort Buddy can use OpenAI (existing functionality preserved)
   - [ ] Sort Buddy can connect to Gmail with app passwords
   - [ ] Sort Buddy can connect to Yahoo with app passwords
   - [ ] Sort Buddy can connect to generic IMAP (existing functionality preserved)
   - [ ] Provider selection is configuration-driven
   - [ ] Backward compatibility with existing `.env` files

2. **Code Quality Requirements:**
   - [ ] All code has type hints
   - [ ] No naked exception handling
   - [ ] No `exit()` calls in library code
   - [ ] Configuration validation on startup
   - [ ] No code duplication
   - [ ] mypy strict mode compliance

3. **Testing Requirements:**
   - [ ] Test coverage ≥ 80% for modified modules
   - [ ] All tests pass with `--disable-socket`
   - [ ] No real network calls in unit tests
   - [ ] Tests for both OpenAI and Ollama paths
   - [ ] Tests for all three email providers
   - [ ] Error path tests for all critical operations

4. **Security Requirements:**
   - [ ] No secret leakage in error messages
   - [ ] Configuration validation prevents missing credentials
   - [ ] IMAP SSL/TLS explicitly configured
   - [ ] Input validation on all user inputs
   - [ ] Security audit passed

5. **Documentation Requirements:**
   - [ ] README updated with new configuration options
   - [ ] Provider-specific setup instructions
   - [ ] `.env.dist` includes all new variables
   - [ ] Code has docstrings for all public functions
   - [ ] Architecture documented

### Per-Wave Acceptance Criteria

**Wave 1 (Foundation):**
- [ ] Type hints added to all existing code
- [ ] Logging infrastructure implemented
- [ ] Configuration validation working
- [ ] Duplicate code removed
- [ ] `exit()` calls replaced with exceptions
- [ ] Test infrastructure in place
- [ ] Unit tests for existing code passing

**Wave 2 (AI Layer):**
- [ ] AI client interface defined
- [ ] OpenAI client migrated and tested
- [ ] Ollama client implemented and tested
- [ ] Client factory working
- [ ] Prompt templates extracted
- [ ] `main.py` using factory
- [ ] Tests for AI layer passing
- [ ] `.env.dist` updated

**Wave 3 (Email Layer):**
- [ ] Email provider interface defined
- [ ] Generic IMAP migrated and tested
- [ ] Gmail provider implemented and tested
- [ ] Yahoo provider implemented and tested
- [ ] Provider factory working
- [ ] Email parsing extracted
- [ ] `main.py` using factory
- [ ] Tests for email layer passing
- [ ] `.env.dist` updated

**Wave 4 (Integration):**
- [ ] README updated
- [ ] Provider setup instructions added
- [ ] End-to-end testing passed
- [ ] Security review passed
- [ ] Python review passed
- [ ] Backward compatibility verified

**Wave 5 (Verification):**
- [ ] Full test suite passing
- [ ] Coverage ≥ 80%
- [ ] mypy strict mode passing
- [ ] Security audit passed
- [ ] Release notes prepared
- [ ] Git commit created

## Risks and Rollbacks

### Risks

**High Risk:**
1. **Breaking existing configurations** - If backward compatibility mapping fails
   - **Mitigation:** Extensive testing with existing `.env` files
   - **Rollback:** Revert to old configuration loading logic

2. **Ollama cold-start timeouts** - Users may experience long waits
   - **Mitigation:** Clear documentation, configurable timeout, health check
   - **Rollback:** Increase default timeout or add retry logic

**Medium Risk:**
3. **Gmail/Yahoo authentication changes** - Providers may deprecate app passwords
   - **Mitigation:** Document OAuth2 as future work, monitor provider announcements
   - **Rollback:** Continue supporting generic IMAP

4. **Test coverage gaps** - Complex mocking may miss edge cases
   - **Mitigation:** Add integration tests (local only), manual testing
   - **Rollback:** Add more unit tests for uncovered paths

5. **Type hint errors** - mypy strict mode may reveal hidden bugs
   - **Mitigation:** Address incrementally, use `# type: ignore` sparingly
   - **Rollback:** Relax mypy settings temporarily

**Low Risk:**
6. **Dependency conflicts** - New dependencies may conflict with existing
   - **Mitigation:** Test in fresh environment, use poetry lock
   - **Rollback:** Pin specific versions

7. **Performance regression** - Abstraction layers may add overhead
   - **Mitigation:** Benchmark before/after, optimize hot paths
   - **Rollback:** Simplify abstractions if needed

### Rollback Procedures

**Per-Wave Rollback:**

**Wave 1 Rollback:**
- Revert type hints (if causing issues)
- Revert logging to `print()`
- Remove configuration validation
- Restore duplicate code
- Restore `exit()` calls
- Remove test infrastructure

**Wave 2 Rollback:**
- Delete `src/ai/` directory
- Restore `src/ai.py` to original
- Revert `main.py` to use direct `configure_openai()`
- Remove Ollama variables from `.env.dist`

**Wave 3 Rollback:**
- Delete `src/email/` directory
- Restore `src/email_fetcher.py` to original
- Revert `main.py` to use direct `EmailFetcher`
- Remove Gmail/Yahoo variables from `.env.dist`

**Wave 4 Rollback:**
- Revert README changes
- Remove provider-specific documentation

**Wave 5 Rollback:**
- Abandon merge, delete branch
- Start fresh with revised plan

**Complete Rollback:**
- Delete feature branch
- Checkout main branch
- All changes are isolated to feature branch

### Monitoring Post-Deployment

**Metrics to Track:**
1. Error rate (AI API failures, IMAP connection failures)
2. Processing time per email
3. User-reported issues with new providers
4. Configuration validation failures

**Success Criteria:**
- Error rate ≤ existing baseline
- Processing time within 2x of baseline
- No breaking user reports within 1 week

## Open Questions

1. **OAuth2 Timeline:** Should OAuth2 for Gmail/Yahoo be included in this implementation or deferred to a future phase? (Current plan: defer)
2. **Streaming Support:** Should streaming responses be added for better UX with slow Ollama models? (Current plan: defer)
3. **Model Warmup:** Should we implement model pre-loading for Ollama to reduce cold-start latency? (Current plan: defer, document as future work)
4. **Connection Pooling:** Should we implement IMAP connection pooling for multiple accounts? (Current plan: defer, single account only)
5. **State Persistence:** Should we add state tracking (processed emails) for resume capability? (Current plan: defer)
6. **Test Coverage Target:** Is 80% coverage appropriate, or should we aim higher? (Current plan: 80% minimum)
7. **mypy Strict Mode:** Should we enforce strict mode from day 1, or allow gradual compliance? (Current plan: aim for strict, use `# type: ignore` sparingly)

## Appendix: Review Summaries

### Architecture Review Summary
**Verdict:** NEEDS_REFACTOR
- Functional but lacks structural sophistication
- Tight coupling to OpenAI and generic IMAP
- No configuration management or data models
- Duplicate utility functions
- Recommended abstraction layers for AI and email providers

### Python Code Review Summary
**Verdict:** CRITICAL ISSUES
- No type hints (zero)
- Naked exception handling with `exit()`
- No environment variable validation
- IMAP connection in `__init__` (untestable)
- No test coverage
- Unused dependencies

### Security Audit Summary
**Verdict:** PASS (with recommendations)
- Good credential management via environment variables
- SSL/TLS enabled for IMAP
- Potential secret leakage in error messages
- No configuration validation
- Need input validation improvements
- Ollama security considerations documented

### Ollama Integration Review Summary
**Verdict:** FAIL for production-ready support
- Can technically hit Ollama endpoint but brittle
- No timeout configuration
- Rate limit headers will fail
- Module-level global state (untestable)
- `exit()` on error (crashes tests)
- Response parsing brittle

### Testing Review Summary
**Verdict:** FAIL - zero test coverage
- No tests exist
- Need pytest infrastructure
- IMAP connection in `__init__` blocks unit testing
- `exit()` in `ai.py` crashes pytest
- Recommended comprehensive test plan with mocking strategy
