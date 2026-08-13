# Security Audit: Ollama/IMAP Integration

**Project:** Sort Buddy  
**Branch:** `feature/ollama-imap-integration`  
**Auditor:** security-auditor  
**Date:** 2026-08-12  
**Scope:** Secret handling, IMAP credentials, API keys, injection risks, and input validation for Ollama and IMAP integration

---

## Executive Summary

**Overall Verdict:** **PASS** (with recommendations)

The Sort Buddy application demonstrates a reasonable baseline for security practices, particularly in credential management through environment variables. However, several areas require attention before adding Ollama and Gmail/Yahoo IMAP support:

- **Critical Issues:** None identified
- **Warnings:** 5 issues requiring attention
- **Info:** 7 best practice recommendations

The current implementation properly uses environment variables for secrets, has SSL/TLS enabled for IMAP, and avoids common injection patterns. The main concerns revolve around input validation, error handling, and the specific security requirements for Gmail/Yahoo OAuth2.

---

## 1. Credential Handling

### Current Implementation

**Status:** ✅ **GOOD** - Credentials are properly managed via environment variables

The application correctly uses environment variables for all sensitive data:

```python
# src/ai.py
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.base_url = os.getenv("OPENAI_API_URL")

# src/email_fetcher.py
self.host = os.getenv("IMAP_HOST")
self.username = os.getenv("EMAIL_USERNAME")
self.password = os.getenv("EMAIL_PASSWORD")
```

**Environment Variable Template (.env.dist):**
```
OPENAI_API_KEY="[your-openai-api-key]"
OPENAI_API_URL="https://api.openai.com/v1/"
OPENAI_MODEL="gpt-4-turbo"
FOLDER_PREFIX="AI-"
IMAP_HOST="[imap.somehost.com]"
EMAIL_USERNAME="[your email]"
EMAIL_PASSWORD="[your password]"
```

### Findings

✅ **PASS:** `.env` is properly listed in `.gitignore`  
✅ **PASS:** No hardcoded credentials found in source code  
✅ **PASS:** `.env.dist` uses placeholder values, not real secrets  
✅ **PASS:** Credentials are loaded via `python-dotenv` and accessed via `os.getenv()`

### Ollama Integration Considerations

When adding Ollama support, the current pattern works well:

```python
# Already supported in .env.dist:
#OPENAI_API_URL="http://localhost:11434/v1/"
#OPENAI_MODEL="dolphin-mixtral:latest"
```

**Security Note:** Ollama's default configuration binds to `0.0.0.0:11434`, which may expose the API to network access. Users should:
1. Configure Ollama to bind to `127.0.0.1:11434` for local-only access
2. Use a reverse proxy with authentication if remote access is needed
3. Consider adding `OLLAMA_API_KEY` support if Ollama instance is network-accessible

---

## 2. Secret Leakage Risks

### Code Review

**Status:** ⚠️ **WARNING** - Potential secret leakage in error messages and debug output

#### Issue 1: Error Messages May Expose Sensitive Information

**Location:** `src/ai.py:76`
```python
except Exception as e:
    print(f"Error in calling OpenAI API: {e}")
    exit()
```

**Risk:** The exception object `e` may contain sensitive information including:
- API keys (if malformed in request)
- Request URLs with query parameters
- Internal service details

**Recommendation:** Implement sanitized error logging:
```python
except Exception as e:
    print(f"Error in calling OpenAI API: {type(e).__name__}")
    if os.getenv("DEBUG"):
        print(f"Details: {e}")
    exit()
```

#### Issue 2: IMAP Error Messages

**Location:** `src/email_fetcher.py:99`
```python
except Exception as e:
    print(f"An error occurred: {e}")
```

**Risk:** Similar to above, may expose IMAP credentials or server details.

**Recommendation:** Same sanitization approach as Issue 1.

#### Issue 3: Debug Output May Contain Email Content

**Location:** `src/ai.py:32-34`
```python
if show_prompt:
    print(system_prompt)
    print(prompt)
```

**Risk:** The `prompt` variable contains the full email body, which may include:
- Personal information
- Password reset links
- Sensitive business data

**Current Mitigation:** The `--show-prompt` flag is user-controlled and defaults to off.

**Recommendation:** Add a warning when `--show-prompt` is used:
```python
if show_prompt:
    print("WARNING: Email content will be displayed in plaintext")
    print(system_prompt)
    print(prompt)
```

### Log File Analysis

**Status:** ✅ **PASS** - No logging framework detected

The application uses `print()` statements rather than a logging framework, which reduces the risk of secrets being written to log files. However, this also means:

- No structured logging
- No log level control
- No log rotation
- Output may be captured by shell redirection

**Recommendation:** Consider implementing Python's `logging` module with:
- Configurable log levels
- Secret redaction middleware
- File rotation
- Separate log files for different components

### JSON Output

**Location:** `src/util.py:27-33`, `src/main.py:89-91`

**Status:** ⚠️ **WARNING** - JSON files may contain sensitive email content

The `--save-to-json` feature saves complete email content to JSON files:
```python
def save_results_to_json(ai_folders, messages, filename):
    results = {
        "ai_folders": ai_folders,
        "messages": messages  # Contains full email bodies
    }
```

**Current Mitigation:** `.gitignore` includes `*.json`, preventing accidental commits.

**Recommendation:**
1. Add file permission restrictions when saving JSON (mode `0600`)
2. Add a warning when `--save-to-json` is used
3. Consider encrypting JSON output if it contains sensitive data
4. Add option to redact email bodies in JSON output

---

## 3. Input Validation and Injection Risks

### Email Content Processing

**Status:** ⚠️ **WARNING** - Limited input validation on email content

#### Issue 1: No Validation of Email Content Before AI Processing

**Location:** `src/ai.py:29-36`
```python
prompt = f"Email Subject: {message['subject']}\n"
prompt += f"Email From: {message['from']}\n"
# ...
prompt += f"Email Body: {message['body']}\n"
```

**Risk:** Email content is directly interpolated into the prompt without validation. While this doesn't pose a direct injection risk to the OpenAI API (which sanitizes input), it could:
- Cause prompt injection attacks against the AI model
- Exceed token limits
- Cause unexpected behavior

**Recommendation:**
1. Add content length validation
2. Sanitize or truncate extremely long emails
3. Consider adding prompt injection detection/mitigation
4. Validate email structure before processing

#### Issue 2: Folder Name Validation

**Location:** `src/ai.py:92-93`
```python
elif folder not in folders:
    return (f"invalid: \"{folder}\"", explanation)
```

**Status:** ✅ **GOOD** - Folder names are validated against allowed list

The application correctly validates that AI-suggested folders are in the allowed list before moving messages.

#### Issue 3: IMAP Search Criteria

**Location:** `src/email_fetcher.py:25`
```python
search_criteria = ['UNSEEN', 'NOT', 'KEYWORD', flag]
```

**Status:** ✅ **GOOD** - Search criteria are hardcoded, not user-controlled

The IMAP search criteria are not constructed from user input, eliminating injection risk.

### CLI Argument Validation

**Status:** ⚠️ **WARNING** - Limited validation of CLI arguments

**Location:** `src/main.py:96-104`

The application uses `argparse` but has limited validation:
- `--limit` accepts any integer (no range validation)
- `--save-to-json` accepts any path (no path validation)
- `--use-json` accepts any path (no path validation)

**Recommendation:**
1. Add range validation for `--limit` (e.g., 1-1000)
2. Add path validation for `--save-to-json` and `--use-json`
3. Prevent directory traversal via path arguments
4. Add file existence checks for `--use-json`

### HTML Processing

**Location:** `src/email_fetcher.py:54-56, 61-63`

**Status:** ✅ **GOOD** - BeautifulSoup used for HTML sanitization

```python
soup = BeautifulSoup(html_content, 'html.parser')
text_content += soup.get_text()
```

The application correctly uses BeautifulSoup to extract text from HTML, which:
- Removes HTML tags
- Reduces XSS risk
- Provides clean text for AI processing

**Recommendation:** Consider adding additional sanitization for:
- Script tags
- Embedded JavaScript
- External resource references

---

## 4. IMAP Security Considerations

### Current Implementation

**Status:** ✅ **GOOD** - SSL/TLS enabled by default

**Location:** `src/email_fetcher.py:15`
```python
self.imapclient = IMAPClient(self.host, ssl=True)
```

The application correctly uses SSL for IMAP connections, which:
- Encrypts credentials in transit
- Prevents man-in-the-middle attacks
- Is required by modern email providers

### Gmail/Yahoo Specific Considerations

#### Issue 1: App Passwords vs OAuth2

**Current Approach:** The application uses username/password authentication.

**Gmail Requirements:**
- Gmail no longer supports basic username/password authentication for third-party apps
- Users must use App Passwords (for less secure apps) or OAuth2
- App Passwords are specific to each application and can be revoked

**Yahoo Requirements:**
- Yahoo also requires App Passwords for third-party access
- OAuth2 is the recommended approach

**Recommendation:**
1. **Short-term:** Document that users must generate App Passwords for Gmail/Yahoo
2. **Long-term:** Implement OAuth2 authentication for:
   - Gmail (using Google OAuth2)
   - Yahoo (using Yahoo OAuth2)
3. Add support for OAuth2 token refresh
4. Store OAuth2 tokens securely (encrypted at rest)

#### Issue 2: No IMAP Connection Timeout Configuration

**Location:** `src/email_fetcher.py:15`

**Current:** No timeout specified for IMAP connection.

**Risk:** Long-running connections may:
- Hang indefinitely
- Consume resources
- Fail to detect network issues

**Recommendation:** Add connection timeout configuration:
```python
self.imapclient = IMAPClient(self.host, ssl=True, timeout=30)
```

#### Issue 3: No Certificate Validation Control

**Location:** `src/email_fetcher.py:15`

**Current:** SSL is enabled but certificate validation behavior is not explicitly controlled.

**Risk:** If `imapclient` defaults to no certificate validation, MITM attacks are possible.

**Recommendation:** Explicitly enable certificate validation:
```python
self.imapclient = IMAPClient(
    self.host, 
    ssl=True,
    ssl_context=ssl.create_default_context()
)
```

#### Issue 4: IMAP Host Validation

**Location:** `src/email_fetcher.py:10`

**Current:** IMAP host is loaded from environment variable without validation.

**Risk:** If environment is compromised, attacker could redirect to malicious IMAP server.

**Recommendation:** Add IMAP host validation:
1. Validate host format (hostname or IP)
2. Consider adding a whitelist of allowed IMAP hosts
3. Add DNSSEC validation if possible

### IMAP Operation Security

#### Issue 1: Message Deletion Without Confirmation

**Location:** `src/email_fetcher.py:91-96`
```python
def move_message(self, message_id, target_folder):
    try:
        self.imapclient.copy(message_id, target_folder)
        self.imapclient.delete_messages([message_id])
        self.imapclient.expunge()
```

**Risk:** Messages are permanently deleted after copy. If copy fails but delete succeeds, data is lost.

**Current Mitigation:** `dry_run` mode prevents actual operations.

**Recommendation:**
1. Verify copy succeeded before delete
2. Add transaction-like behavior (copy → verify → delete → expunge)
3. Consider adding a "trash" intermediate folder
4. Log all deletions for audit trail

#### Issue 2: No Rate Limiting

**Current:** No rate limiting on IMAP operations.

**Risk:** Aggressive email processing may:
- Trigger IMAP server rate limits
- Cause account suspension
- Impact other email clients

**Recommendation:** Add rate limiting:
1. Implement delay between IMAP operations
2. Track operation counts per time window
3. Add exponential backoff on errors
4. Respect IMAP server rate limit headers

---

## 5. API Endpoint Security (Ollama vs OpenAI)

### Current Implementation

**Status:** ✅ **GOOD** - Flexible API URL configuration

**Location:** `src/ai.py:5-6`
```python
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.base_url = os.getenv("OPENAI_API_URL")
```

The application correctly uses the OpenAI SDK's `base_url` parameter, which allows switching between:
- OpenAI API (`https://api.openai.com/v1/`)
- Ollama (`http://localhost:11434/v1/`)
- Other OpenAI-compatible APIs

### Ollama-Specific Security Considerations

#### Issue 1: No API Key Validation for Ollama

**Current:** The application always sets `openai.api_key`, even for Ollama.

**Ollama Behavior:** Ollama's OpenAI-compatible API may not require or validate API keys by default.

**Risk:** If Ollama is configured without authentication:
- Any local process can access the API
- Network-exposed Ollama instances are vulnerable to unauthorized access

**Recommendation:**
1. Add conditional API key setting:
```python
api_url = os.getenv("OPENAI_API_URL")
if not api_url.startswith("http://localhost") and not api_url.startswith("http://127.0.0.1"):
    openai.api_key = os.getenv("OPENAI_API_KEY")
```
2. Document Ollama security requirements
3. Recommend Ollama authentication for network deployments

#### Issue 2: No SSL/TLS for Local Ollama

**Current:** Ollama URL in `.env.dist` uses `http://` not `https://`:
```
#OPENAI_API_URL="http://localhost:11434/v1/"
```

**Risk:** While localhost HTTP is generally safe, it's best practice to use HTTPS even locally.

**Recommendation:**
1. Document that HTTP is acceptable for localhost
2. Recommend HTTPS for remote Ollama instances
3. Add SSL context configuration for custom CA certificates

#### Issue 3: No API Endpoint Validation

**Current:** No validation that the configured API URL is reachable or valid.

**Risk:** Misconfiguration may lead to:
- Silent failures
- Requests to unintended endpoints
- Debugging difficulties

**Recommendation:**
1. Add API endpoint health check on startup
2. Validate URL format
3. Test connectivity before processing emails
4. Add clear error messages for connection failures

### OpenAI-Specific Security Considerations

#### Issue 1: API Key Exposure in Rate Limit Output

**Location:** `src/ai.py:58-69`

**Status:** ✅ **GOOD** - Rate limit headers do not contain API keys

The rate limit headers printed by `--print-rate-limits` do not contain sensitive information.

#### Issue 2: No API Key Scope Validation

**Current:** No validation that the API key has appropriate permissions.

**Risk:** API key may have:
- Insufficient permissions (causing failures)
- Excessive permissions (violating principle of least privilege)

**Recommendation:**
1. Document required API key permissions
2. Add optional API key validation on startup
3. Test API key with minimal required scope

---

## 6. Dependency Safety

### Current Dependencies

**Status:** ⚠️ **WARNING** - Unable to run `safety check` (poetry not available in environment)

**Dependencies from pyproject.toml:**
```
python = "^3.10"
numpy = "^1.26.4"
pandas = "^2.2.2"
scikit-learn = "^1.4.2"
openai = "^1.26.0"
python-dotenv = "^1.0.1"
mail-parser = "^3.15.0"
imapclient = "^3.0.1"
beautifulsoup4 = "^4.12.3"
lxml = "^5.2.1"
colorama = "^0.4.6"
```

### Version Pinning Analysis

**Status:** ⚠️ **WARNING** - Caret notation allows minor version updates

All dependencies use `^` (caret) notation, which allows:
- Minor version updates (e.g., `1.26.0` → `1.26.1` → `1.27.0`)
- Patch updates are always allowed
- Major version updates are not allowed

**Risk:** Minor version updates may introduce:
- Breaking changes
- Security vulnerabilities
- Behavioral changes

**Recommendation:**
1. Run `safety check` or `pip-audit` regularly
2. Consider pinning exact versions for production deployments
3. Implement dependency update testing
4. Subscribe to security advisories for dependencies

### Known Vulnerability Scan

**Status:** ⚠️ **WARNING** - Unable to complete scan in current environment

**Recommendation:** Before production deployment:
1. Run `poetry audit` or `safety check`
2. Review CVE database for current dependency versions
3. Update any vulnerable dependencies
4. Document dependency update process

### Unused Dependencies

**Observation:** The following dependencies may be unused:
- `numpy`, `pandas`, `scikit-learn` - Not imported in source files
- `mail-parser` - Not imported in source files (custom email parsing used)

**Recommendation:**
1. Verify if these are needed for future features
2. Remove unused dependencies to reduce attack surface
3. Document why each dependency is required

---

## 7. Authentication and Authorization

### Current State

**Status:** ℹ️ **INFO** - No authentication/authorization implemented

The application is a CLI tool that:
- Runs with user's credentials
- Has no multi-user support
- Has no role-based access control
- Has no API endpoints to protect

### Ollama/IMAP Integration Impact

**Status:** ℹ️ **INFO** - No new auth requirements for current architecture

The planned Ollama/IMAP integration does not introduce new authentication requirements for the application itself, as it continues to be a CLI tool.

**Recommendation:** If the application evolves to:
- Web interface → Implement session management
- Multi-user support → Implement user authentication
- API endpoints → Implement API key authentication
- Background service → Implement service account management

---

## 8. Docker Security

### Current State

**Status:** ℹ️ **INFO** - No Docker configuration present

The project does not currently include Docker configuration files.

**Recommendation for Future Dockerization:**
1. Use non-root user in containers
2. Scan base images for vulnerabilities
3. Use multi-stage builds to reduce attack surface
4. Implement secrets management (Docker Secrets, environment files)
5. Scan images with tools like Trivy or Snyk
6. Sign images for verification
7. Implement resource limits

---

## 9. Testing and Verification

### Current Test Coverage

**Status:** ❌ **FAIL** - No tests present

**Observation:** The `tests/` directory contains only `__init__.py` with no test files.

**Risk:** Without tests, security fixes may:
- Introduce regressions
- Fail to catch edge cases
- Not be validated for correctness

**Recommendation:**
1. Add unit tests for security-critical functions:
   - Credential loading
   - Input validation
   - Folder name validation
   - Email content sanitization
2. Add integration tests for:
   - IMAP connection with SSL
   - OpenAI API calls
   - Ollama API calls
3. Add security tests:
   - Secret leakage detection
   - Input fuzzing
   - Authentication failure scenarios
4. Implement test coverage reporting (target: 80%+)

### Mocking Strategy

**Status:** ℹ️ **INFO** - No mocking framework selected

**Recommendation:** Use `pytest-mock` for:
- Mocking OpenAI API calls
- Mocking IMAP connections
- Mocking environment variables
- Testing error scenarios

---

## 10. Configuration Security

### Environment Variable Loading

**Status:** ✅ **GOOD** - Uses python-dotenv

**Location:** `src/main.py:12`
```python
from dotenv import load_dotenv
load_dotenv()
```

**Observation:** The application loads `.env` from the current working directory.

**Risk:** If run from different directories, may load wrong `.env` file.

**Recommendation:**
1. Specify explicit path to `.env` file
2. Add validation that required environment variables are set
3. Provide clear error messages for missing configuration
4. Consider supporting multiple environment profiles (dev, prod, test)

### Configuration Validation

**Status:** ❌ **FAIL** - No configuration validation

**Risk:** Missing or invalid configuration may cause:
- Runtime errors
- Silent misconfigurations
- Security vulnerabilities

**Recommendation:** Add configuration validation:
```python
def validate_config():
    required_vars = [
        "OPENAI_API_KEY",
        "OPENAI_API_URL",
        "OPENAI_MODEL",
        "IMAP_HOST",
        "EMAIL_USERNAME",
        "EMAIL_PASSWORD",
        "FOLDER_PREFIX"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
```

---

## 11. Recommendations Summary

### Critical (Fix Immediately)

None identified.

### Warnings (Fix Soon)

1. **Sanitize error messages** to prevent secret leakage
2. **Add input validation** for email content and CLI arguments
3. **Implement OAuth2** for Gmail/Yahoo (long-term)
4. **Add IMAP transaction safety** (verify before delete)
5. **Add rate limiting** for IMAP operations
6. **Implement configuration validation** on startup
7. **Add tests** for security-critical functionality

### Info (Best Practices)

1. **Document Ollama security requirements** (localhost binding, authentication)
2. **Add logging framework** with secret redaction
3. **Implement JSON file encryption** for saved email data
4. **Add IMAP connection timeout** configuration
5. **Implement certificate validation** for IMAP
6. **Run dependency vulnerability scans** regularly
7. **Remove unused dependencies** (numpy, pandas, scikit-learn, mail-parser)
8. **Add Docker security** if containerizing

### Ollama-Specific Recommendations

1. Document that Ollama should bind to `127.0.0.1:11434` for local-only access
2. Add conditional API key setting (skip for localhost)
3. Recommend HTTPS for remote Ollama instances
4. Add Ollama health check on startup
5. Document Ollama authentication options

### Gmail/Yahoo-Specific Recommendations

1. Document App Password requirements for Gmail/Yahoo
2. Implement OAuth2 authentication (long-term)
3. Add OAuth2 token refresh logic
4. Implement secure token storage (encryption at rest)
5. Add OAuth2 scope validation

---

## 12. Implementation Priority

### Phase 1: Before Ollama/IMAP Integration

1. Add configuration validation
2. Sanitize error messages
3. Add input validation for CLI arguments
4. Add basic test coverage
5. Run dependency vulnerability scan

### Phase 2: During Ollama/IMAP Integration

1. Add Ollama health check
2. Add conditional API key setting
3. Document Ollama security requirements
4. Add IMAP connection timeout
5. Implement IMAP transaction safety
6. Add IMAP rate limiting

### Phase 3: Post-Integration (Gmail/Yahoo Support)

1. Document App Password requirements
2. Implement OAuth2 authentication
3. Add OAuth2 token management
4. Add OAuth2-specific tests
5. Document OAuth2 setup process

---

## 13. Security Checklist for Implementation

### Credential Management
- [ ] All credentials in environment variables
- [ ] `.env` in `.gitignore`
- [ ] No hardcoded secrets in code
- [ ] Secret redaction in error messages
- [ ] Secure token storage for OAuth2

### Input Validation
- [ ] Email content length validation
- [ ] Email content sanitization
- [ ] CLI argument validation
- [ ] Path traversal prevention
- [ ] Folder name validation

### IMAP Security
- [ ] SSL/TLS enabled
- [ ] Certificate validation
- [ ] Connection timeout configured
- [ ] App Password support for Gmail/Yahoo
- [ ] OAuth2 support (long-term)
- [ ] Rate limiting
- [ ] Transaction safety (verify before delete)

### API Security
- [ ] API endpoint validation
- [ ] Conditional API key for localhost
- [ ] HTTPS for remote endpoints
- [ ] Health check on startup
- [ ] Error message sanitization

### Data Protection
- [ ] JSON file encryption option
- [ ] File permission restrictions (0600)
- [ ] Warning for sensitive output
- [ ] Logging with secret redaction
- [ ] Secure OAuth2 token storage

### Testing
- [ ] Unit tests for security functions
- [ ] Integration tests for IMAP/API
- [ ] Security tests (fuzzing, injection)
- [ ] Test coverage reporting
- [ ] Mocking for external dependencies

### Dependencies
- [ ] Regular vulnerability scans
- [ ] Dependency update process
- [ ] Remove unused dependencies
- [ ] Document dependency requirements

---

## 14. Conclusion

The Sort Buddy application has a solid foundation for security, with proper credential management and SSL/TLS enabled for IMAP. The main areas requiring attention are:

1. **Input validation** - Add validation for email content and CLI arguments
2. **Error handling** - Sanitize error messages to prevent secret leakage
3. **IMAP safety** - Add transaction safety and rate limiting
4. **Testing** - Implement comprehensive test coverage
5. **OAuth2** - Plan for OAuth2 implementation for Gmail/Yahoo

The Ollama integration can be implemented securely with the current architecture, provided that:
- Ollama is configured to bind to localhost
- Conditional API key setting is implemented
- Health checks are added
- Security requirements are documented

For Gmail/Yahoo support, the short-term solution is to document App Password requirements, with OAuth2 as a long-term enhancement.

**Overall Assessment:** The application is ready for Ollama/IMAP integration with the recommended security improvements implemented in phases.

---

**Audit Completed:** 2026-08-12  
**Next Review:** After Phase 1 implementation  
**Auditor:** security-auditor
