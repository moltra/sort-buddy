# Ollama + IMAP Integration - Detailed Implementation Tasks

**Date:** 2026-08-12
**Planner:** planner agent
**Branch:** feature/ollama-imap-integration
**Total Tasks:** 45

## Task List

### Wave 1: Foundation (Foundation Refactor)

#### Task 1.1: Add Type Hints to Existing Code
- **Title:** Add comprehensive type hints to all existing Python files
- **Description:** Add type hints to all functions in `src/main.py`, `src/ai.py`, `src/email_fetcher.py`, `src/json_email_fetcher.py`, and `src/util.py` using Python 3.10+ syntax (`str | None`, `list[str]`, etc.)
- **Owner:** python-developer
- **Files:** `src/main.py`, `src/ai.py`, `src/email_fetcher.py`, `src/json_email_fetcher.py`, `src/util.py`
- **Order:** 1
- **Acceptance Criteria:**
  - All functions have type hints for parameters and return values
  - mypy runs without errors (may have warnings initially)
  - No `Any` types used except where unavoidable
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Low

#### Task 1.2: Implement Logging Infrastructure
- **Title:** Replace print() statements with Python logging module
- **Description:** Implement Python's `logging` module with proper configuration. Replace all `print()` statements with appropriate log levels (DEBUG, INFO, WARNING, ERROR). Separate user-facing output from debug logs.
- **Owner:** python-developer
- **Files:** `src/main.py`, `src/ai.py`, `src/email_fetcher.py`, `src/util.py`
- **Order:** 2
- **Acceptance Criteria:**
  - Logging configured with levels and formatting
  - User-facing output preserved (colorama for CLI)
  - Debug output uses logging module
  - Log levels used appropriately (INFO for normal operations, ERROR for failures)
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Low

#### Task 1.3: Create Configuration Management Module
- **Title:** Implement Pydantic-based configuration validation
- **Description:** Create `src/config.py` with Pydantic models for configuration validation. Load configuration from environment variables with validation. Provide clear error messages for missing/invalid values.
- **Owner:** python-developer
- **Files:** `src/config.py` (new)
- **Order:** 3
- **Acceptance Criteria:**
  - Pydantic models for all configuration values
  - Environment variable loading with validation
  - Clear error messages for missing/invalid configuration
  - URL validation for API endpoints
  - Email format validation for email addresses
- **Verification:** python-reviewer, security-auditor
- **Priority:** High
- **Risk:** Medium

#### Task 1.4: Remove Duplicate Code
- **Title:** Remove duplicate utility functions from ai.py
- **Description:** Remove duplicate `remove_prefix()` and `get_stripped_folder_list()` functions from `src/ai.py`. Import from `src/util.py` instead.
- **Owner:** python-developer
- **Files:** `src/ai.py`, `src/util.py`
- **Order:** 4
- **Acceptance Criteria:**
  - Duplicate functions removed from `ai.py`
  - Functions imported from `util.py`
  - All tests still pass
  - No functionality changes
- **Verification:** python-reviewer
- **Priority:** Medium
- **Risk:** Low

#### Task 1.5: Replace exit() Calls with Exceptions
- **Title:** Replace exit() calls with raised exceptions
- **Description:** Replace all `exit()` calls in library code (`src/ai.py`, `src/email_fetcher.py`) with raised exceptions. Update `src/main.py` to catch exceptions and handle gracefully.
- **Owner:** python-developer
- **Files:** `src/ai.py`, `src/email_fetcher.py`, `src/main.py`
- **Order:** 5
- **Acceptance Criteria:**
  - No `exit()` calls in library code
  - Domain-specific exceptions raised (e.g., `AIError`, `IMAPError`)
  - Main loop catches exceptions and handles gracefully
  - Error messages preserved
- **Verification:** python-reviewer, testing-guardian
- **Priority:** High
- **Risk:** Medium

#### Task 1.6: Add Test Infrastructure
- **Title:** Set up pytest infrastructure with fixtures
- **Description:** Add pytest, pytest-mock, pytest-cov, pytest-socket to dependencies. Create `tests/conftest.py` with shared fixtures for mocked clients, sample messages, and environment variables. Create `tests/fixtures/` directory structure.
- **Owner:** testing-guardian
- **Files:** `pyproject.toml`, `tests/conftest.py` (new), `tests/fixtures/` (new directory)
- **Order:** 6
- **Acceptance Criteria:**
  - Test dependencies added to pyproject.toml
  - pytest configured with coverage and socket blocking
  - Shared fixtures created (mock IMAP, mock OpenAI, sample emails)
  - Fixture data files created (sample .eml files, mock responses)
- **Verification:** qa-ci-agent
- **Priority:** High
- **Risk:** Low

#### Task 1.7: Add Unit Tests for Existing Code
- **Title:** Add unit tests for existing modules
- **Description:** Add comprehensive unit tests for `src/util.py`, `src/ai.py`, `src/email_fetcher.py`, `src/json_email_fetcher.py`, and `src/main.py`. Use mocks for external dependencies. Ensure tests pass with `--disable-socket`.
- **Owner:** testing-guardian
- **Files:** `tests/unit/test_util.py` (new), `tests/unit/test_ai.py` (new), `tests/unit/test_email_fetcher.py` (new), `tests/unit/test_json_email_fetcher.py` (new), `tests/unit/test_main.py` (new)
- **Order:** 7
- **Acceptance Criteria:**
  - Unit tests for all existing modules
  - Tests pass with `--disable-socket`
  - Coverage ≥ 70% for existing code
  - Error paths tested
- **Verification:** qa-ci-agent
- **Priority:** High
- **Risk:** Medium

### Wave 2: AI Layer Abstraction (Ollama Integration)

#### Task 2.1: Create AI Client Interface
- **Title:** Define abstract base class for AI clients
- **Description:** Create `src/ai/base.py` with abstract `AIClient` class defining the interface for AI providers (configure, classify_email, health_check).
- **Owner:** python-developer
- **Files:** `src/ai/base.py` (new), `src/ai/__init__.py` (new)
- **Order:** 8
- **Acceptance Criteria:**
  - Abstract base class defined
  - Methods: configure(), classify_email(), health_check()
  - Type hints on all methods
  - Docstrings for all methods
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Low

#### Task 2.2: Migrate OpenAI Logic to OpenAI Client
- **Title:** Extract OpenAI implementation to separate module
- **Description:** Migrate existing OpenAI logic from `src/ai.py` to `src/ai/openai_client.py`. Implement the `AIClient` interface. Handle OpenAI-specific rate limit headers. Use explicit client instance instead of module-level globals.
- **Owner:** ollama-specialist, python-developer
- **Files:** `src/ai/openai_client.py` (new)
- **Order:** 9
- **Acceptance Criteria:**
  - OpenAI client implements AIClient interface
  - Explicit OpenAI client instance (not module-level globals)
  - Rate limit header parsing implemented
  - Timeout configuration (default 30s for cloud API)
  - Error handling for OpenAI-specific errors
- **Verification:** ollama-specialist, python-reviewer
- **Priority:** High
- **Risk:** Medium

#### Task 2.3: Implement Ollama Client
- **Title:** Create Ollama-specific AI client implementation
- **Description:** Create `src/ai/ollama_client.py` implementing the `AIClient` interface. Handle Ollama-specific behavior: longer timeout (60s default), no rate limit headers, placeholder API key, model validation.
- **Owner:** ollama-specialist
- **Files:** `src/ai/ollama_client.py` (new)
- **Order:** 10
- **Acceptance Criteria:**
  - Ollama client implements AIClient interface
  - Timeout configuration (default 60s for local models)
  - Rate limit header handling (skip if absent)
  - Placeholder API key for local instances
  - Model validation (check via /api/tags or handle 404)
  - Error handling for Ollama-specific errors (connection, not found)
- **Verification:** ollama-specialist, python-reviewer
- **Priority:** High
- **Risk:** Medium

#### Task 2.4: Create AI Client Factory
- **Title:** Implement factory for AI client creation
- **Description:** Create `src/ai/factory.py` with `create_ai_client()` function. Read `LLM_PROVIDER` environment variable and instantiate appropriate client. Handle backward compatibility mapping from legacy `OPENAI_*` variables.
- **Owner:** python-developer
- **Files:** `src/ai/factory.py` (new)
- **Order:** 11
- **Acceptance Criteria:**
  - Factory function creates correct client based on provider
  - Backward compatibility mapping implemented
  - Clear error for unknown provider
  - Configuration passed to client
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Low

#### Task 2.5: Extract Prompt Templates
- **Title:** Move prompt generation to separate module
- **Description:** Create `src/ai/prompts.py` with prompt template functions. Extract prompt generation logic from string concatenation to template-based approach. Support both OpenAI and Ollama prompt formats.
- **Owner:** python-developer
- **Files:** `src/ai/prompts.py` (new)
- **Order:** 12
- **Acceptance Criteria:**
  - Prompt templates defined as functions
  - System prompt and user prompt separated
  - Folder list formatting logic extracted
  - Template-based approach (not string concatenation)
- **Verification:** python-reviewer
- **Priority:** Medium
- **Risk:** Low

#### Task 2.6: Update main.py to Use AI Factory
- **Title:** Refactor main.py to use AI client factory
- **Description:** Update `src/main.py` to use `create_ai_client()` instead of direct `configure_openai()`. Pass client to AI functions. Remove dependency on module-level OpenAI state.
- **Owner:** python-developer
- **Files:** `src/main.py`
- **Order:** 13
- **Acceptance Criteria:**
  - main.py uses factory to create AI client
  - Client passed to AI functions
  - No module-level OpenAI state usage
  - Backward compatibility preserved
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Medium

#### Task 2.7: Add Tests for AI Layer
- **Title:** Add unit tests for AI client implementations
- **Description:** Add comprehensive unit tests for `src/ai/base.py`, `src/ai/openai_client.py`, `src/ai/ollama_client.py`, `src/ai/factory.py`, and `src/ai/prompts.py`. Mock OpenAI API calls. Test both providers.
- **Owner:** testing-guardian
- **Files:** `tests/unit/test_ai/` (new directory), `tests/unit/test_ai/test_openai_client.py` (new), `tests/unit/test_ai/test_ollama_client.py` (new), `tests/unit/test_ai/test_factory.py` (new), `tests/unit/test_ai/test_prompts.py` (new)
- **Order:** 14
- **Acceptance Criteria:**
  - Tests for all AI modules
  - OpenAI client tested with rate limit headers
  - Ollama client tested without rate limit headers
  - Factory tested for both providers
  - Prompt templates tested
  - All tests pass with `--disable-socket`
  - Coverage ≥ 80% for AI layer
- **Verification:** qa-ci-agent
- **Priority:** High
- **Risk:** Medium

#### Task 2.8: Update .env.dist with Ollama Variables
- **Title:** Add Ollama configuration to .env.dist
- **Description:** Update `.env.dist` to include `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT`, and Ollama-specific variables. Document backward compatibility mapping.
- **Owner:** python-developer
- **Files:** `.env.dist`
- **Order:** 15
- **Acceptance Criteria:**
  - New LLM_* variables added with comments
  - Ollama-specific variables documented
  - Backward compatibility mapping explained
  - Clear examples for both OpenAI and Ollama
- **Verification:** documentation-agent
- **Priority:** Medium
- **Risk:** Low

### Wave 3: Email Layer Abstraction (IMAP Provider Support)

#### Task 3.1: Create Email Provider Interface
- **Title:** Define abstract base class for email providers
- **Description:** Create `src/email/base.py` with abstract `EmailProvider` class defining the interface for email providers (connect, list_ai_folders, fetch_next_message, move_message, has_more_messages, close).
- **Owner:** python-developer
- **Files:** `src/email/base.py` (new), `src/email/__init__.py` (new)
- **Order:** 16
- **Acceptance Criteria:**
  - Abstract base class defined
  - Methods: connect(), list_ai_folders(), fetch_next_message(), move_message(), has_more_messages(), close()
  - Type hints on all methods
  - Docstrings for all methods
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Low

#### Task 3.2: Migrate Generic IMAP Logic
- **Title:** Extract generic IMAP implementation to separate module
- **Description:** Migrate existing `EmailFetcher` logic from `src/email_fetcher.py` to `src/email/generic_imap.py`. Implement the `EmailProvider` interface. Separate configuration from connection (for testability). Add connection retry logic and timeout configuration.
- **Owner:** python-developer
- **Files:** `src/email/generic_imap.py` (new)
- **Order:** 17
- **Acceptance Criteria:**
  - Generic IMAP provider implements EmailProvider interface
  - Configuration separated from connection
  - Connection retry logic with exponential backoff
  - Timeout configuration
  - Improved error handling for connection failures
  - Existing functionality preserved
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Medium

#### Task 3.3: Implement Gmail Provider
- **Title:** Create Gmail-specific email provider implementation
- **Description:** Create `src/email/gmail_provider.py` implementing the `EmailProvider` interface. Handle Gmail-specific settings: host (imap.gmail.com), port (993), SSL (true), app password authentication, Gmail labels.
- **Owner:** python-developer
- **Files:** `src/email/gmail_provider.py` (new)
- **Order:** 18
- **Acceptance Criteria:**
  - Gmail provider implements EmailProvider interface
  - Default host: imap.gmail.com, port: 993, SSL: true
  - App password authentication
  - Gmail label handling
  - Gmail-specific search syntax if needed
  - Error handling for Gmail-specific failures
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Medium

#### Task 3.4: Implement Yahoo Provider
- **Title:** Create Yahoo-specific email provider implementation
- **Description:** Create `src/email/yahoo_provider.py` implementing the `EmailProvider` interface. Handle Yahoo-specific settings: host (imap.mail.yahoo.com), port (993), SSL (true), app password authentication, Yahoo folder structure.
- **Owner:** python-developer
- **Files:** `src/email/yahoo_provider.py` (new)
- **Order:** 19
- **Acceptance Criteria:**
  - Yahoo provider implements EmailProvider interface
  - Default host: imap.mail.yahoo.com, port: 993, SSL: true
  - App password authentication
  - Yahoo folder structure handling
  - Yahoo-specific IMAP quirks handled
  - Error handling for Yahoo-specific failures
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Medium

#### Task 3.5: Create Email Provider Factory
- **Title:** Implement factory for email provider creation
- **Description:** Create `src/email/factory.py` with `create_email_provider()` function. Read `EMAIL_PROVIDER` environment variable and instantiate appropriate provider. Handle backward compatibility with legacy `IMAP_*` variables for generic provider.
- **Owner:** python-developer
- **Files:** `src/email/factory.py` (new)
- **Order:** 20
- **Acceptance Criteria:**
  - Factory function creates correct provider based on EMAIL_PROVIDER
  - Backward compatibility with IMAP_* variables for generic provider
  - Clear error for unknown provider
  - Configuration passed to provider
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Low

#### Task 3.6: Extract Email Parsing Logic
- **Title:** Move email parsing to separate module
- **Description:** Create `src/email/parsers.py` with email parsing functions. Extract email parsing logic from providers (HTML to text conversion, multipart handling, envelope parsing).
- **Owner:** python-developer
- **Files:** `src/email/parsers.py` (new)
- **Order:** 21
- **Acceptance Criteria:**
  - Email parsing functions extracted
  - HTML to text conversion logic
  - Multipart message handling
  - Envelope parsing
  - Safe decoding logic
  - Used by all providers
- **Verification:** python-reviewer
- **Priority:** Medium
- **Risk:** Low

#### Task 3.7: Update main.py to Use Email Factory
- **Title:** Refactor main.py to use email provider factory
- **Description:** Update `src/main.py` to use `create_email_provider()` instead of direct `EmailFetcher` instantiation. Pass provider to email operations. Remove dependency on specific email fetcher class.
- **Owner:** python-developer
- **Files:** `src/main.py`
- **Order:** 22
- **Acceptance Criteria:**
  - main.py uses factory to create email provider
  - Provider interface used for all email operations
  - No direct EmailFetcher instantiation
  - Backward compatibility preserved
  - JSONEmailFetcher still works via --use-json flag
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Medium

#### Task 3.8: Add Tests for Email Layer
- **Title:** Add unit tests for email provider implementations
- **Description:** Add comprehensive unit tests for `src/email/base.py`, `src/email/generic_imap.py`, `src/email/gmail_provider.py`, `src/email/yahoo_provider.py`, `src/email/factory.py`, and `src/email/parsers.py`. Mock IMAPClient. Test all providers.
- **Owner:** testing-guardian
- **Files:** `tests/unit/test_email/` (new directory), `tests/unit/test_email/test_generic_imap.py` (new), `tests/unit/test_email/test_gmail_provider.py` (new), `tests/unit/test_email/test_yahoo_provider.py` (new), `tests/unit/test_email/test_factory.py` (new), `tests/unit/test_email/test_parsers.py` (new)
- **Order:** 23
- **Acceptance Criteria:**
  - Tests for all email modules
  - Generic IMAP provider tested
  - Gmail provider tested with provider-specific behavior
  - Yahoo provider tested with provider-specific behavior
  - Factory tested for all providers
  - Email parsers tested with various email formats
  - All tests pass with `--disable-socket`
  - Coverage ≥ 80% for email layer
- **Verification:** qa-ci-agent
- **Priority:** High
- **Risk:** Medium

#### Task 3.9: Update .env.dist with Gmail/Yahoo Variables
- **Title:** Add Gmail/Yahoo configuration to .env.dist
- **Description:** Update `.env.dist` to include `EMAIL_PROVIDER`, `GMAIL_USERNAME`, `GMAIL_APP_PASSWORD`, `YAHOO_USERNAME`, `YAHOO_APP_PASSWORD`. Document app password requirements for both providers.
- **Owner:** python-developer
- **Files:** `.env.dist`
- **Order:** 24
- **Acceptance Criteria:**
  - New EMAIL_PROVIDER variable added
  - Gmail-specific variables documented
  - Yahoo-specific variables documented
  - App password requirements explained
  - Clear examples for all three providers
- **Verification:** documentation-agent
- **Priority:** Medium
- **Risk:** Low

### Wave 4: Integration and Documentation

#### Task 4.1: Update README with New Configuration
- **Title:** Document new configuration options in README
- **Description:** Update `README.md` to document new `LLM_*` and `EMAIL_PROVIDER` variables. Explain how to configure OpenAI, Ollama, Gmail, Yahoo, and generic IMAP. Add examples for each provider combination.
- **Owner:** documentation-agent
- **Files:** `README.md`
- **Order:** 25
- **Acceptance Criteria:**
  - New configuration options documented
  - Provider selection explained
  - Examples for OpenAI + generic IMAP
  - Examples for Ollama + generic IMAP
  - Examples for OpenAI + Gmail
  - Examples for Ollama + Gmail
  - Examples for OpenAI + Yahoo
  - Examples for Ollama + Yahoo
  - Backward compatibility explained
- **Verification:** documentation-agent
- **Priority:** High
- **Risk:** Low

#### Task 4.2: Add Provider-Specific Setup Instructions
- **Title:** Document provider-specific setup requirements
- **Description:** Add detailed setup instructions for Gmail (app password generation) and Yahoo (app password generation). Document Ollama installation and model pulling. Include troubleshooting tips.
- **Owner:** documentation-agent
- **Files:** `README.md`
- **Order:** 26
- **Acceptance Criteria:**
  - Gmail app password generation steps
  - Yahoo app password generation steps
  - Ollama installation instructions
  - Ollama model pulling instructions
  - Troubleshooting common issues
  - Links to provider documentation
- **Verification:** documentation-agent
- **Priority:** High
- **Risk:** Low

#### Task 4.3: Update run.sh if Needed
- **Title:** Verify and update run.sh script
- **Description:** Review `run.sh` to ensure it works with new structure. Update if needed to handle new environment variables or module structure.
- **Owner:** python-developer
- **Files:** `run.sh`
- **Order:** 27
- **Acceptance Criteria:**
  - run.sh works with new module structure
  - No changes needed, or changes documented
  - Script handles new environment variables if needed
- **Verification:** python-reviewer
- **Priority:** Low
- **Risk:** Low

#### Task 4.4: End-to-End Testing
- **Title:** Perform end-to-end testing with both providers
- **Description:** Test the complete application with both OpenAI and Ollama AI providers. Test with generic IMAP, Gmail, and Yahoo email providers. Verify all combinations work correctly.
- **Owner:** testing-guardian
- **Files:** None (testing only)
- **Order:** 28
- **Acceptance Criteria:**
  - OpenAI + generic IMAP works
  - Ollama + generic IMAP works
  - OpenAI + Gmail works (if credentials available)
  - Ollama + Gmail works (if credentials available)
  - OpenAI + Yahoo works (if credentials available)
  - Ollama + Yahoo works (if credentials available)
  - Backward compatibility with old .env files works
  - All CLI flags work with new structure
- **Verification:** qa-ci-agent
- **Priority:** High
- **Risk:** Medium

#### Task 4.5: Security Review of New Code
- **Title:** Perform security audit on new code
- **Description:** Security auditor reviews all new code for secret handling, input validation, error handling, and provider-specific security considerations. Focus on Ollama and Gmail/Yahoo integration.
- **Owner:** security-auditor
- **Files:** All new code in `src/ai/`, `src/email/`, `src/config.py`, modified files
- **Order:** 29
- **Acceptance Criteria:**
  - No secret leakage in error messages
  - Configuration validation prevents missing credentials
  - IMAP SSL/TLS explicitly configured
  - Input validation on all user inputs
  - Ollama security considerations addressed
  - Gmail/Yahoo app password security documented
  - No new security vulnerabilities introduced
- **Verification:** security-auditor
- **Priority:** High
- **Risk:** Low

#### Task 4.6: Python Code Review
- **Title:** Perform Python code review on all changes
- **Description:** Python reviewer reviews all code for style, patterns, error handling, type hints, and maintainability. Ensure mypy compliance and code quality standards.
- **Owner:** python-reviewer
- **Files:** All modified and new Python files
- **Order:** 30
- **Acceptance Criteria:**
  - Code follows Python best practices
  - Type hints correct and complete
  - Error handling appropriate
  - No code duplication
  - mypy strict mode compliance
  - Docstrings present for public functions
  - Import ordering correct (isort)
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Low

#### Task 4.7: Backward Compatibility Testing
- **Title:** Verify backward compatibility with existing configurations
- **Description:** Test that existing `.env` files with old variable names (`OPENAI_API_KEY`, `IMAP_HOST`, etc.) still work without modification. Verify legacy configuration mapping works correctly.
- **Owner:** testing-guardian
- **Files:** None (testing only)
- **Order:** 31
- **Acceptance Criteria:**
  - Old .env files work without changes
  - Legacy variable mapping works
  - No breaking changes for existing users
  - Migration path documented
- **Verification:** qa-ci-agent
- **Priority:** High
- **Risk:** Medium

### Wave 5: Verification and Release

#### Task 5.1: Run Full Test Suite with Coverage
- **Title:** Execute complete test suite with coverage reporting
- **Description:** Run full pytest suite with coverage reporting. Ensure coverage ≥ 80% for modified modules. All tests must pass.
- **Owner:** qa-ci-agent
- **Files:** None (testing only)
- **Order:** 32
- **Acceptance Criteria:**
  - All tests pass
  - Coverage ≥ 80% for `src/ai/`, `src/email/`, `src/config.py`, `src/main.py`
  - Coverage report generated
  - No tests skipped without reason
- **Verification:** qa-ci-agent
- **Priority:** High
- **Risk:** Low

#### Task 5.2: mypy Strict Mode Compliance Check
- **Title:** Run mypy strict mode type checking
- **Description:** Run mypy in strict mode on all code. Address any type errors. Use `# type: ignore` sparingly and only where necessary.
- **Owner:** qa-ci-agent
- **Files:** All Python files
- **Order:** 33
- **Acceptance Criteria:**
  - mypy strict mode passes
  - No type errors (except justified `# type: ignore`)
  - Type hints complete and correct
- **Verification:** python-reviewer
- **Priority:** High
- **Risk:** Low

#### Task 5.3: Security Audit Final Check
- **Title:** Final security audit before release
- **Description:** Security auditor performs final review of all changes, including dependencies, configuration, and documentation. Ensure no security regressions.
- **Owner:** security-auditor
- **Files:** All modified files, `pyproject.toml`, `.env.dist`
- **Order:** 34
- **Acceptance Criteria:**
  - No security vulnerabilities introduced
  - Dependencies reviewed for known issues
  - Configuration security verified
  - Documentation security accurate
  - No secrets in code or documentation
- **Verification:** security-auditor
- **Priority:** High
- **Risk:** Low

#### Task 5.4: Integration Testing (Optional, Local)
- **Title:** Optional integration tests with real services
- **Description:** Create optional integration tests that run with real Ollama and IMAP servers. These tests should be skipped by default in CI and only run locally with explicit opt-in.
- **Owner:** testing-guardian
- **Files:** `tests/integration/` (new directory), `tests/integration/test_ollama_integration.py` (new), `tests/integration/test_imap_integration.py` (new)
- **Order:** 35
- **Acceptance Criteria:**
  - Integration tests created
  - Tests skipped by default (marked with pytest markers)
  - Documentation for running locally
  - Tests require real credentials/services
  - CI does not run these tests
- **Verification:** qa-ci-agent
- **Priority:** Low
- **Risk:** Low

#### Task 5.5: Prepare Release Notes
- **Title:** Write release notes for the update
- **Description:** Prepare release notes documenting new features, breaking changes, migration guide, and known issues. Include upgrade instructions for existing users.
- **Owner:** documentation-agent
- **Files:** `RELEASE_NOTES.md` (new)
- **Order:** 36
- **Acceptance Criteria:**
  - New features documented (Ollama, Gmail, Yahoo)
  - Breaking changes listed (none expected)
  - Migration guide for existing users
  - Configuration examples
  - Known issues documented
  - Upgrade instructions
- **Verification:** documentation-agent
- **Priority:** Medium
- **Risk:** Low

#### Task 5.6: Create Git Commit
- **Title:** Create git commit with all changes
- **Description:** Stage and commit all changes with a descriptive commit message following conventional commit format. Ensure no sensitive information is included.
- **Owner:** git-workflow
- **Files:** All modified and new files
- **Order:** 37
- **Acceptance Criteria:**
  - All changes staged
  - Commit message follows conventional commit format
  - No secrets in commit
  - Commit includes all implementation files
  - Commit includes test files
  - Commit includes documentation updates
- **Verification:** git-workflow
- **Priority:** High
- **Risk:** Low

#### Task 5.7: Coordinate Merge to Main
- **Title:** Prepare for merge to main branch
- **Description:** Coordinate with team to merge feature branch to main. Ensure all verification gates passed. Create pull request if needed. Address any final review comments.
- **Owner:** git-workflow
- **Files:** None (coordination only)
- **Order:** 38
- **Acceptance Criteria:**
  - All verification gates passed
  - Pull request created (if using PR workflow)
  - Review comments addressed
  - Merge approved
  - Branch merged to main
- **Verification:** git-workflow
- **Priority:** High
- **Risk:** Low

### Cleanup and Compatibility Tasks

#### Task 5.8: Deprecate Old ai.py
- **Title:** Mark old ai.py as deprecated
- **Description:** Add deprecation warning to `src/ai.py` indicating it's a compatibility wrapper and will be removed in future version. Keep it functional for backward compatibility.
- **Owner:** python-developer
- **Files:** `src/ai.py`
- **Order:** 39
- **Acceptance Criteria:**
  - Deprecation warning added
  - Functionality preserved
  - Warning points to new `src/ai/` package
  - Documentation updated
- **Verification:** python-reviewer
- **Priority:** Low
- **Risk:** Low

#### Task 5.9: Deprecate Old email_fetcher.py
- **Title:** Mark old email_fetcher.py as deprecated
- **Description:** Add deprecation warning to `src/email_fetcher.py` indicating it's a compatibility wrapper and will be removed in future version. Keep it functional for backward compatibility.
- **Owner:** python-developer
- **Files:** `src/email_fetcher.py`
- **Order:** 40
- **Acceptance Criteria:**
  - Deprecation warning added
  - Functionality preserved
  - Warning points to new `src/email/` package
  - Documentation updated
- **Verification:** python-reviewer
- **Priority:** Low
- **Risk:** Low

#### Task 5.10: Remove Unused Dependencies
- **Title:** Clean up unused dependencies from pyproject.toml
- **Description:** Remove unused dependencies (numpy, pandas, scikit-learn, mail-parser) from `pyproject.toml` as identified in reviews. Run `poetry lock --no-update` after changes.
- **Owner:** python-developer
- **Files:** `pyproject.toml`
- **Order:** 41
- **Acceptance Criteria:**
  - Unused dependencies removed
  - poetry lock updated
  - poetry install succeeds
  - All tests still pass
- **Verification:** qa-ci-agent
- **Priority:** Medium
- **Risk:** Low

#### Task 5.11: Add Data Models
- **Title:** Create Pydantic data models for email and classification
- **Description:** Create `src/models/email.py` and `src/models/classification.py` with Pydantic models for Email and ClassificationResult. Use these models instead of raw dictionaries.
- **Owner:** python-developer
- **Files:** `src/models/__init__.py` (new), `src/models/email.py` (new), `src/models/classification.py` (new)
- **Order:** 42
- **Acceptance Criteria:**
  - Email model defined with validation
  - ClassificationResult model defined with validation
  - Models used in place of raw dictionaries
  - Type safety improved
- **Verification:** python-reviewer
- **Priority:** Medium
- **Risk:** Medium

#### Task 5.12: Add Docstrings to All Public Functions
- **Title:** Add comprehensive docstrings to all public functions
- **Description:** Add Google-style or NumPy-style docstrings to all public functions and classes in new modules. Ensure docstrings document parameters, return values, and exceptions.
- **Owner:** python-developer
- **Files:** All new Python files
- **Order:** 43
- **Acceptance Criteria:**
  - All public functions have docstrings
  - Docstrings follow consistent style
  - Parameters documented
  - Return values documented
  - Exceptions documented
- **Verification:** python-reviewer
- **Priority:** Medium
- **Risk:** Low

#### Task 5.13: Add Pre-commit Hooks
- **Title:** Set up pre-commit hooks for quality checks
- **Description:** Configure pre-commit hooks for mypy, pytest, isort, and other quality checks. Add `.pre-commit-config.yaml` file.
- **Owner:** qa-ci-agent
- **Files:** `.pre-commit-config.yaml` (new)
- **Order:** 44
- **Acceptance Criteria:**
  - Pre-commit hooks configured
  - mypy hook included
  - pytest hook included
  - isort hook included
  - Documentation for installing hooks
- **Verification:** qa-ci-agent
- **Priority:** Low
- **Risk:** Low

#### Task 5.14: Final Documentation Review
- **Title:** Review and update all documentation
- **Description:** Review all documentation (README, .env.dist, code comments, docstrings) for accuracy and completeness. Ensure documentation matches implementation.
- **Owner:** documentation-agent
- **Files:** `README.md`, `.env.dist`, all Python files
- **Order:** 45
- **Acceptance Criteria:**
  - README accurate and complete
  - .env.dist includes all variables
  - Code comments accurate
  - Docstrings accurate
  - No outdated information
  - Examples work correctly
- **Verification:** documentation-agent
- **Priority:** Medium
- **Risk:** Low

## Task Dependencies

### Wave 1 Dependencies
- Task 1.1 (type hints) → Task 1.5 (replace exit) - type hints needed before refactoring
- Task 1.3 (config) → Task 1.5 (replace exit) - config needed for better error handling
- Task 1.6 (test infra) → Task 1.7 (unit tests) - infrastructure needed before tests

### Wave 2 Dependencies
- Task 1.1-1.7 (foundation) → All Wave 2 tasks - foundation must be complete
- Task 2.1 (interface) → Task 2.2 (OpenAI client) - interface needed first
- Task 2.1 (interface) → Task 2.3 (Ollama client) - interface needed first
- Task 2.2 (OpenAI) + Task 2.3 (Ollama) → Task 2.4 (factory) - implementations needed first
- Task 2.4 (factory) → Task 2.6 (main.py) - factory needed before main.py update
- Task 2.1-2.6 (implementation) → Task 2.7 (tests) - implementation needed before tests

### Wave 3 Dependencies
- Task 1.1-1.7 (foundation) → All Wave 3 tasks - foundation must be complete
- Task 3.1 (interface) → Task 3.2 (generic IMAP) - interface needed first
- Task 3.1 (interface) → Task 3.3 (Gmail) - interface needed first
- Task 3.1 (interface) → Task 3.4 (Yahoo) - interface needed first
- Task 3.2-3.4 (implementations) → Task 3.5 (factory) - implementations needed first
- Task 3.5 (factory) → Task 3.7 (main.py) - factory needed before main.py update
- Task 3.1-3.7 (implementation) → Task 3.8 (tests) - implementation needed before tests

### Wave 4 Dependencies
- Wave 2 complete → Task 4.4 (E2E testing) - AI layer needed
- Wave 3 complete → Task 4.4 (E2E testing) - email layer needed
- Wave 2 + Wave 3 complete → Task 4.5 (security review) - all code needed
- Wave 2 + Wave 3 complete → Task 4.6 (Python review) - all code needed

### Wave 5 Dependencies
- Wave 4 complete → All Wave 5 tasks - integration must be complete
- Task 5.1 (tests) → Task 5.2 (mypy) - tests should pass first
- Task 5.1 (tests) + Task 5.2 (mypy) → Task 5.3 (security) - quality checks first
- Task 5.1-5.3 (verification) → Task 5.6 (commit) - verification before commit

## Parallelization Opportunities

### Highly Parallelizable (can run simultaneously)
- Task 2.2 (OpenAI client) and Task 2.3 (Ollama client) - independent implementations
- Task 3.2 (generic IMAP), Task 3.3 (Gmail), Task 3.4 (Yahoo) - independent implementations
- Task 2.7 (AI tests) and Task 3.8 (email tests) - independent test suites
- Task 4.5 (security review) and Task 4.6 (Python review) - independent reviews

### Moderately Parallelizable (can run with some coordination)
- Task 1.1 (type hints) across multiple files - can split by file
- Task 1.7 (unit tests) across multiple modules - can split by module
- Task 2.8 (.env.dist) and Task 3.9 (.env.dist) - can merge into single task

### Sequential (must run in order)
- Wave 1 → Wave 2 → Wave 3 → Wave 4 → Wave 5 - waves are sequential
- Interface definitions → Implementations → Factory → Tests - within each wave
- Implementation → Tests → Review → Commit - verification pipeline

## File Ownership Summary

### New Files (no conflicts)
- `src/config.py` - python-developer
- `src/models/` - python-developer
- `src/ai/` - ollama-specialist, python-developer
- `src/email/` - python-developer
- `tests/` - testing-guardian
- `tests/fixtures/` - testing-guardian
- `RELEASE_NOTES.md` - documentation-agent
- `.pre-commit-config.yaml` - qa-ci-agent

### Modified Files (sequential access)
- `src/main.py` - python-developer (modified in tasks 1.1, 1.2, 1.5, 2.6, 3.7)
- `src/ai.py` - python-developer (modified in tasks 1.1, 1.2, 1.4, 1.5, 5.8)
- `src/email_fetcher.py` - python-developer (modified in tasks 1.1, 1.2, 1.5, 5.9)
- `src/json_email_fetcher.py` - python-developer (modified in task 1.1)
- `src/util.py` - python-developer (modified in tasks 1.1, 1.2, 1.4)
- `.env.dist` - python-developer (modified in tasks 2.8, 3.9)
- `pyproject.toml` - python-developer (modified in tasks 1.6, 5.10)
- `README.md` - documentation-agent (modified in tasks 4.1, 4.2)
- `run.sh` - python-developer (modified in task 4.3)

## Risk Mitigation

### High-Risk Tasks
- Task 1.5 (replace exit) - Medium risk: may break error handling
  - Mitigation: Comprehensive testing, gradual rollout
- Task 2.6 (main.py AI factory) - Medium risk: may break existing workflows
  - Mitigation: Backward compatibility testing, gradual migration
- Task 3.7 (main.py email factory) - Medium risk: may break existing workflows
  - Mitigation: Backward compatibility testing, gradual migration

### Medium-Risk Tasks
- Task 1.3 (config validation) - Medium risk: may reject valid configurations
  - Mitigation: Extensive testing with various configurations
- Task 3.2 (generic IMAP refactor) - Medium risk: may introduce bugs
  - Mitigation: Comprehensive test coverage, parallel implementation
- Task 3.3 (Gmail provider) - Medium risk: provider-specific quirks
  - Mitigation: Research Gmail IMAP behavior, test with real account
- Task 3.4 (Yahoo provider) - Medium risk: provider-specific quirks
  - Mitigation: Research Yahoo IMAP behavior, test with real account

### Low-Risk Tasks
- All documentation tasks
- All test infrastructure tasks
- All cleanup tasks
- All verification tasks

## Success Metrics

### Code Quality
- Type hint coverage: 100%
- Test coverage: ≥ 80%
- mypy strict mode: Pass
- No code duplication
- No naked exception handling

### Functionality
- OpenAI provider works
- Ollama provider works
- Generic IMAP works
- Gmail provider works
- Yahoo provider works
- Backward compatibility preserved

### Security
- No secret leakage
- Configuration validation works
- SSL/TLS configured
- Input validation present
- Security audit passed

### Documentation
- README updated
- .env.dist complete
- Code documented
- Migration guide available
- Release notes prepared
