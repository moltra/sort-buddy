# Architecture Review: Ollama + IMAP Integration

**Review Date:** 2026-08-12  
**Reviewer:** architecture-reviewer sub-agent  
**Branch:** `feature/ollama-imap-integration`  
**Task ID:** ollama-imap-arch-review

---

## Executive Summary

Sort Buddy is a monolithic Python application with a simple, functional architecture that separates concerns across four main modules: `main.py` (controller/orchestration), `ai.py` (AI service layer), `email_fetcher.py` (IMAP data access), and `util.py` (shared utilities). The current architecture is **functionally sound but lacks the structural sophistication** needed for the proposed Ollama and multi-provider IMAP enhancements. The codebase follows a basic layered pattern but has several architectural debt items that should be addressed before adding new features: duplicate utility functions, tight coupling to OpenAI-specific patterns, and a lack of abstraction for email providers. The application is well-positioned for enhancement but requires refactoring to maintain clean architecture principles as complexity grows.

**Verdict:** **NEEDS_REFACTOR** - The current architecture requires moderate refactoring to support Ollama and multi-provider IMAP cleanly.

---

## Current Module Boundaries and Dependency Graph

### Module Structure

```
src/
├── main.py              # Controller/orchestration layer
├── ai.py                # AI service layer (OpenAI client)
├── email_fetcher.py     # IMAP data access layer
├── json_email_fetcher.py # JSON mock data access layer
└── util.py              # Shared utilities
```

### Dependency Analysis

**Current Dependency Flow:**
```
main.py
  ├── ai.py
  ├── email_fetcher.py
  ├── json_email_fetcher.py
  └── util.py

ai.py
  └── util.py (via removed functions)

email_fetcher.py
  └── util.py

json_email_fetcher.py
  └── (no dependencies)

util.py
  └── (no dependencies)
```

**Dependency Direction Assessment:** ✅ **CORRECT**
- Controllers depend on services → ✅
- Services depend on utilities → ✅
- No circular dependencies detected → ✅
- Utilities do not depend on controllers → ✅

### Module Boundary Review

#### 1. Controller Layer (`main.py`)
**Current State:** 
- ✅ Properly acts as orchestration layer
- ✅ Handles CLI argument parsing
- ✅ Coordinates between AI and email fetcher
- ⚠️ Contains business logic for folder validation (lines 69-79)
- ⚠️ Directly manipulates message data structure

**Issues:**
- **WARNING:** Folder validation logic (lines 69-79) should be in a service layer
- **INFO:** Message response data construction (lines 57-64) could be moved to a model/service

#### 2. AI Service Layer (`ai.py`)
**Current State:**
- ✅ Encapsulates OpenAI API calls
- ✅ Provides clean interface for AI responses
- ⚠️ Tightly coupled to OpenAI-specific API patterns
- ⚠️ Contains duplicate utility functions from `util.py`
- ⚠️ Hard-coded prompt engineering logic

**Issues:**
- **CRITICAL:** Direct OpenAI client usage (line 43) makes Ollama integration difficult
- **WARNING:** Duplicate `remove_prefix()` and `get_stripped_folder_list()` functions (lines 8-14) - these exist in `util.py`
- **WARNING:** System prompt is hard-coded string concatenation (lines 20-27) - should be template-based
- **INFO:** Rate limit handling is OpenAI-specific (lines 58-69)

#### 3. Email Data Access Layer (`email_fetcher.py`)
**Current State:**
- ✅ Encapsulates IMAP operations
- ✅ Provides clean interface for message fetching
- ⚠️ Generic IMAP implementation only
- ⚠️ No abstraction for provider-specific logic
- ⚠️ Tight coupling to IMAPClient library

**Issues:**
- **CRITICAL:** No abstraction layer for different IMAP providers (Gmail, Yahoo, generic)
- **WARNING:** Hard-coded IMAP search criteria (line 25) may not work for all providers
- **INFO:** Folder listing logic (line 34) assumes standard IMAP folder structure
- **INFO:** Message parsing logic (lines 49-63) is complex and could be extracted

#### 4. Mock Data Layer (`json_email_fetcher.py`)
**Current State:**
- ✅ Implements same interface as `EmailFetcher`
- ✅ Useful for testing and benchmarking
- ✅ No external dependencies

**Issues:**
- **INFO:** Good pattern - should be preserved for testing
- **INFO:** Could benefit from formal interface/protocol definition

#### 5. Utilities Layer (`util.py`)
**Current State:**
- ✅ Contains pure utility functions
- ✅ No business logic
- ⚠️ Some functions duplicated in `ai.py`

**Issues:**
- **WARNING:** Function duplication with `ai.py` indicates poor code organization
- **INFO:** Good separation of concerns overall

---

## Current Usage Analysis

### How `ai.py` is Currently Used

**Initialization Flow:**
```python
# main.py line 23
configure_openai()  # Sets global OpenAI client configuration

# main.py line 53
folder, explanation = get_ai_response_from_message(message, formatted_inboxes, show_prompt, show_rate_limits)
```

**Key Functions:**
- `configure_openai()` - Sets global OpenAI API key and base URL from environment
- `get_ai_response_from_message()` - Main entry point for AI classification
- `generate_prompt()` - Constructs system and user prompts
- `get_ai_response()` - Calls OpenAI API and parses response

**Current Limitations for Ollama:**
1. **Global State:** Uses `openai.api_key` and `openai.base_url` as module-level globals
2. **OpenAI-Specific Headers:** Rate limit header parsing (lines 58-69) is OpenAI-specific
3. **No Client Abstraction:** Direct call to `openai.chat.completions.with_raw_response.create()`
4. **No Fallback Logic:** No mechanism to switch between OpenAI and Ollama
5. **No Model Lifecycle:** No warmup/unload logic for local models

### How `email_fetcher.py` is Currently Used

**Initialization Flow:**
```python
# main.py lines 26-30
if use_json:
    fetcher = JSONEmailFetcher(use_json)
else:
    fetcher = EmailFetcher(dry_run)
```

**Key Functions:**
- `__init__()` - Connects to IMAP server, authenticates, selects INBOX
- `list_ai_folders()` - Returns folders matching FOLDER_PREFIX
- `fetch_next_message()` - Fetches and parses next unseen message
- `move_message()` - Moves message to target folder
- `close()` - Logs out from IMAP server

**Current Limitations for Multi-Provider IMAP:**
1. **No Provider Abstraction:** Hard-coded for generic IMAP
2. **No Provider-Specific Configuration:** Single set of IMAP_HOST/USERNAME/PASSWORD
3. **No Provider-Specific Logic:** No handling for Gmail labels, Yahoo folders, etc.
4. **No Authentication Flexibility:** Only basic username/password auth
5. **No Connection Pooling:** Single connection per run

---

## Ollama/OpenAI Integration Architecture

### Recommended Changes

#### 1. AI Client Abstraction Layer

**New File Structure:**
```
src/
├── ai/
│   ├── __init__.py
│   ├── base.py              # Abstract base class/interface
│   ├── openai_client.py     # OpenAI-specific implementation
│   ├── ollama_client.py     # Ollama-specific implementation
│   └── factory.py           # Client factory based on configuration
```

**Interface Definition (`src/ai/base.py`):**
```python
from abc import ABC, abstractmethod
from typing import Tuple, Optional

class AIClient(ABC):
    @abstractmethod
    def configure(self, api_key: str, base_url: str, model: str) -> None:
        """Configure the AI client with credentials and endpoint."""
        pass
    
    @abstractmethod
    def classify_email(
        self, 
        message: dict, 
        folders: list[str],
        show_prompt: bool = False,
        show_rate_limits: bool = False
    ) -> Tuple[str, str]:
        """Classify email and return (folder, explanation)."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the AI service is accessible."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> dict:
        """Return information about the current model."""
        pass
```

**Benefits:**
- ✅ Clean separation between OpenAI and Ollama implementations
- ✅ Easy to add new AI providers in the future
- ✅ Testable through mocking
- ✅ Configuration-driven client selection

#### 2. Configuration-Driven Client Selection

**New Environment Variables:**
```bash
# AI Provider Selection
AI_PROVIDER="openai"  # or "ollama"

# OpenAI Configuration (used when AI_PROVIDER=openai)
OPENAI_API_KEY="[your-openai-api-key]"
OPENAI_API_URL="https://api.openai.com/v1/"
OPENAI_MODEL="gpt-4-turbo"

# Ollama Configuration (used when AI_PROVIDER=ollama)
OLLAMA_API_URL="http://localhost:11434/v1/"
OLLAMA_MODEL="dolphin-mixtral:latest"
OLLAMA_TIMEOUT=300  # Timeout for local model inference
OLLAMA_GPU_MEMORY=8  # Expected GPU memory in GB
```

**Client Factory (`src/ai/factory.py`):**
```python
import os
from .openai_client import OpenAIClient
from .ollama_client import OllamaClient

def create_ai_client() -> AIClient:
    provider = os.getenv("AI_PROVIDER", "openai")
    
    if provider == "openai":
        client = OpenAIClient()
        client.configure(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_URL"),
            model=os.getenv("OPENAI_MODEL")
        )
    elif provider == "ollama":
        client = OllamaClient()
        client.configure(
            api_key="ollama",  # Ollama doesn't require real API key
            base_url=os.getenv("OLLAMA_API_URL"),
            model=os.getenv("OLLAMA_MODEL")
        )
    else:
        raise ValueError(f"Unknown AI provider: {provider}")
    
    return client
```

#### 3. Ollama-Specific Considerations

**Model Lifecycle Management:**
- **Warmup Strategy:** Implement model pre-loading on application start
- **Unload Strategy:** Implement model unloading on application shutdown
- **Health Checks:** Implement endpoint health checks before processing
- **Timeout Handling:** Longer timeouts for local model inference
- **GPU Memory:** Monitor and report GPU memory usage

**Structured Output:**
- Ollama supports OpenAI-compatible API but may have different response formats
- Implement response parsing that handles both OpenAI and Ollama variations
- Consider using JSON mode for more reliable structured output

**Rate Limiting:**
- Ollama doesn't provide rate limit headers
- Implement client-side rate limiting for local models
- Gracefully handle missing rate limit headers

#### 4. Refactoring Existing `ai.py`

**Migration Strategy:**
1. **Phase 1:** Create new `src/ai/` package structure
2. **Phase 2:** Move existing OpenAI logic to `src/ai/openai_client.py`
3. **Phase 3:** Create `src/ai/ollama_client.py` with Ollama-specific logic
4. **Phase 4:** Update `main.py` to use factory pattern
5. **Phase 5:** Deprecate old `ai.py` (keep as compatibility shim)

**Backward Compatibility:**
- Keep `ai.py` as a thin wrapper that calls the new factory
- This allows gradual migration without breaking existing workflows

---

## IMAP Provider-Specific Architecture

### Recommended Changes

#### 1. Email Provider Abstraction Layer

**New File Structure:**
```
src/
├── email/
│   ├── __init__.py
│   ├── base.py              # Abstract base class/interface
│   ├── generic_imap.py      # Generic IMAP implementation
│   ├── gmail_provider.py    # Gmail-specific implementation
│   ├── yahoo_provider.py    # Yahoo-specific implementation
│   └── factory.py           # Provider factory based on configuration
```

**Interface Definition (`src/email/base.py`):**
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class EmailProvider(ABC):
    @abstractmethod
    def connect(self, dry_run: bool = False) -> None:
        """Connect to the email provider."""
        pass
    
    @abstractmethod
    def list_ai_folders(self, prefix: str) -> List[str]:
        """List folders matching the AI prefix."""
        pass
    
    @abstractmethod
    def fetch_next_message(self) -> Optional[Dict]:
        """Fetch the next unread message."""
        pass
    
    @abstractmethod
    def move_message(self, message_id: str, target_folder: str) -> bool:
        """Move message to target folder."""
        pass
    
    @abstractmethod
    def has_more_messages(self) -> bool:
        """Check if there are more messages to process."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the connection."""
        pass
```

#### 2. Provider-Specific Configuration

**New Environment Variables:**
```bash
# Email Provider Selection
EMAIL_PROVIDER="generic"  # or "gmail", "yahoo"

# Generic IMAP Configuration
IMAP_HOST="[imap.somehost.com]"
IMAP_PORT=993
IMAP_USE_SSL=true
EMAIL_USERNAME="[your email]"
EMAIL_PASSWORD="[your password]"

# Gmail-Specific Configuration
GMAIL_USERNAME="[your@gmail.com]"
GMAIL_APP_PASSWORD="[your app password]"
GMAIL_LABEL_PREFIX="AI-"

# Yahoo-Specific Configuration
YAHOO_USERNAME="[your@yahoo.com]"
YAHOO_APP_PASSWORD="[your app password]"
YAHOO_FOLDER_PREFIX="AI-"
```

**Provider Factory (`src/email/factory.py`):**
```python
import os
from .generic_imap import GenericIMAPProvider
from .gmail_provider import GmailProvider
from .yahoo_provider import YahooProvider

def create_email_provider(dry_run: bool = False) -> EmailProvider:
    provider = os.getenv("EMAIL_PROVIDER", "generic")
    
    if provider == "gmail":
        email_provider = GmailProvider()
        email_provider.configure(
            username=os.getenv("GMAIL_USERNAME"),
            password=os.getenv("GMAIL_APP_PASSWORD"),
            label_prefix=os.getenv("GMAIL_LABEL_PREFIX", "AI-")
        )
    elif provider == "yahoo":
        email_provider = YahooProvider()
        email_provider.configure(
            username=os.getenv("YAHOO_USERNAME"),
            password=os.getenv("YAHOO_APP_PASSWORD"),
            folder_prefix=os.getenv("YAHOO_FOLDER_PREFIX", "AI-")
        )
    else:  # generic
        email_provider = GenericIMAPProvider()
        email_provider.configure(
            host=os.getenv("IMAP_HOST"),
            port=int(os.getenv("IMAP_PORT", "993")),
            use_ssl=os.getenv("IMAP_USE_SSL", "true").lower() == "true",
            username=os.getenv("EMAIL_USERNAME"),
            password=os.getenv("EMAIL_PASSWORD"),
            folder_prefix=os.getenv("FOLDER_PREFIX", "AI-")
        )
    
    email_provider.connect(dry_run=dry_run)
    return email_provider
```

#### 3. Provider-Specific Implementations

**Gmail Provider (`src/email/gmail_provider.py`):**
- Handle Gmail-specific authentication (OAuth2 or app passwords)
- Handle Gmail labels instead of traditional folders
- Implement Gmail-specific search syntax
- Handle Gmail's threading model
- Implement Gmail API rate limiting

**Yahoo Provider (`src/email/yahoo_provider.py`):**
- Handle Yahoo-specific authentication (app passwords)
- Handle Yahoo folder structure
- Implement Yahoo-specific search criteria
- Handle Yahoo's IMAP quirks

**Generic IMAP Provider (`src/email/generic_imap.py`):**
- Refactor existing `email_fetcher.py` logic
- Make it more robust for different IMAP servers
- Improve error handling for connection issues
- Add connection retry logic

#### 4. Authentication Flexibility

**Authentication Types to Support:**
1. **Basic Auth:** Username/password (current implementation)
2. **App Passwords:** Gmail/Yahoo app passwords
3. **OAuth2:** Gmail OAuth2 (future enhancement)
4. **XOAUTH2:** Yahoo OAuth2 (future enhancement)

**Authentication Strategy:**
- Start with app passwords for Gmail/Yahoo
- Design architecture to support OAuth2 in future
- Keep authentication logic provider-specific

---

## Suggested File/Directory Ownership

### Proposed New Structure

```
sort-buddy/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Controller (refactored)
│   ├── config.py                  # Configuration management (NEW)
│   ├── models/                    # Data models (NEW)
│   │   ├── __init__.py
│   │   ├── email.py               # Email message model
│   │   └── classification.py      # Classification result model
│   ├── ai/                        # AI service layer (NEW)
│   │   ├── __init__.py
│   │   ├── base.py                # AI client interface
│   │   ├── openai_client.py       # OpenAI implementation
│   │   ├── ollama_client.py       # Ollama implementation
│   │   ├── factory.py             # Client factory
│   │   └── prompts.py             # Prompt templates (NEW)
│   ├── email/                     # Email service layer (NEW)
│   │   ├── __init__.py
│   │   ├── base.py                # Email provider interface
│   │   ├── generic_imap.py        # Generic IMAP implementation
│   │   ├── gmail_provider.py      # Gmail implementation
│   │   ├── yahoo_provider.py      # Yahoo implementation
│   │   ├── factory.py             # Provider factory
│   │   └── parsers.py             # Email parsing logic (NEW)
│   └── util.py                    # Utilities (refactored)
├── tests/
│   ├── __init__.py
│   ├── test_ai/                   # AI tests (NEW)
│   │   ├── __init__.py
│   │   ├── test_openai_client.py
│   │   ├── test_ollama_client.py
│   │   └── test_factory.py
│   ├── test_email/                # Email tests (NEW)
│   │   ├── __init__.py
│   │   ├── test_generic_imap.py
│   │   ├── test_gmail_provider.py
│   │   ├── test_yahoo_provider.py
│   │   └── test_factory.py
│   ├── test_models/               # Model tests (NEW)
│   │   ├── __init__.py
│   │   ├── test_email.py
│   │   └── test_classification.py
│   └── test_util.py               # Utility tests (NEW)
├── .env.dist                      # Updated with new variables
├── pyproject.toml                 # Updated dependencies
└── README.md                      # Updated documentation
```

### File Ownership for Implementation

**Phase 1: Foundation (Architecture Refactor)**
- `src/config.py` - python-developer
- `src/models/` - python-developer
- `src/util.py` (refactor) - python-developer

**Phase 2: AI Layer (Ollama Integration)**
- `src/ai/` - ollama-specialist + python-developer
- `tests/test_ai/` - testing-guardian

**Phase 3: Email Layer (Multi-Provider IMAP)**
- `src/email/` - python-developer
- `tests/test_email/` - testing-guardian

**Phase 4: Integration (Controller Updates)**
- `src/main.py` (refactor) - python-developer
- `.env.dist` (update) - python-developer
- `README.md` (update) - documentation-agent

**Phase 5: Testing & Verification**
- All tests - testing-guardian
- Security review - security-auditor
- Python review - python-reviewer

---

## Structural Risks and Inconsistencies

### Critical Issues

#### 1. No Configuration Management
**Risk:** Configuration scattered across environment variables and hard-coded values
**Impact:** Difficult to manage multiple configurations, no validation
**Recommendation:** Create `src/config.py` with Pydantic models for configuration validation

#### 2. No Data Models
**Risk:** Message data passed as raw dictionaries
**Impact:** Type safety issues, difficult to validate, no documentation
**Recommendation:** Create Pydantic models for Email, ClassificationResult, etc.

#### 3. Tight Coupling to OpenAI
**Risk:** `ai.py` directly uses OpenAI client without abstraction
**Impact:** Difficult to add Ollama, testing challenges
**Recommendation:** Implement AI client abstraction layer

#### 4. No Provider Abstraction for Email
**Risk:** `email_fetcher.py` is generic IMAP only
**Impact:** Cannot support Gmail/Yahoo-specific features
**Recommendation:** Implement email provider abstraction layer

### Warning Issues

#### 5. Code Duplication
**Risk:** `remove_prefix()` and `get_stripped_folder_list()` duplicated in `ai.py` and `util.py`
**Impact:** Maintenance burden, potential inconsistencies
**Recommendation:** Remove duplicates, keep only in `util.py`

#### 6. Hard-coded Prompts
**Risk:** System prompt constructed via string concatenation
**Impact:** Difficult to maintain, no versioning, no A/B testing
**Recommendation:** Move to template-based prompts in `src/ai/prompts.py`

#### 7. Error Handling Inconsistency
**Risk:** Some functions exit() on error, others return error tuples
**Impact:** Unpredictable error handling, difficult to test
**Recommendation:** Implement consistent error handling strategy

#### 8. No Logging
**Risk:** Print statements used for output
**Impact:** Difficult to debug in production, no log levels
**Recommendation:** Implement proper logging with Python logging module

### Info Issues

#### 9. No Health Checks
**Risk:** No validation that services are accessible before processing
**Impact:** Failures occur mid-processing, poor user experience
**Recommendation:** Implement health checks for AI and email services

#### 10. No Retry Logic
**Risk:** Network failures cause immediate exit
**Impact:** Unreliable processing, poor resilience
**Recommendation:** Implement exponential backoff retry logic

#### 11. No Connection Pooling
**Risk:** Single IMAP connection per run
**Impact:** Inefficient for high-volume processing
**Recommendation:** Consider connection pooling for future scalability

#### 12. No Telemetry/Metrics
**Risk:** No visibility into performance or errors
**Impact:** Difficult to monitor production usage
**Recommendation:** Consider adding metrics collection (future enhancement)

---

## Cross-Cutting Concerns

### Logging Strategy
**Current:** Print statements with colorama
**Recommended:** Python logging module with structured output
**Implementation:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

### Error Handling Strategy
**Current:** Mixed - some exit(), some return tuples
**Recommended:** Custom exception hierarchy
**Implementation:**
```python
class SortBuddyError(Exception):
    """Base exception for Sort Buddy."""
    pass

class AIError(SortBuddyError):
    """AI-related errors."""
    pass

class EmailProviderError(SortBuddyError):
    """Email provider errors."""
    pass

class ConfigurationError(SortBuddyError):
    """Configuration errors."""
    pass
```

### Configuration Validation
**Current:** Environment variables read directly, no validation
**Recommended:** Pydantic models for configuration
**Implementation:**
```python
from pydantic import BaseModel, Field, validator

class AIConfig(BaseModel):
    provider: str = Field(default="openai")
    openai_api_key: str
    openai_api_url: str = "https://api.openai.com/v1/"
    openai_model: str = "gpt-4-turbo"
    ollama_api_url: str = "http://localhost:11434/v1/"
    ollama_model: str = "dolphin-mixtral:latest"
    
    @validator('provider')
    def validate_provider(cls, v):
        if v not in ['openai', 'ollama']:
            raise ValueError(f"Invalid AI provider: {v}")
        return v
```

### Testing Strategy
**Current:** No tests (empty tests directory)
**Recommended:** Comprehensive test suite with mocking
**Implementation:**
- Unit tests for each client/provider
- Integration tests with mock servers
- Configuration validation tests
- Error handling tests

---

## Dependency Graph Validation

### Current Dependencies (from pyproject.toml)
```
numpy ^1.26.4
pandas ^2.2.2
scikit-learn ^1.4.2
openai ^1.26.0
python-dotenv ^1.0.1
mail-parser ^3.15.0
imapclient ^3.0.1
beautifulsoup4 ^4.12.3
lxml ^5.2.1
colorama ^0.4.6
```

### Recommended New Dependencies
```
# Existing (keep)
python-dotenv ^1.0.1
imapclient ^3.0.1
beautifulsoup4 ^4.12.3
lxml ^5.2.1
colorama ^0.4.6

# New for configuration
pydantic ^2.0.0
pydantic-settings ^2.0.0

# New for testing
pytest ^7.0.0
pytest-mock ^3.10.0
pytest-cov ^4.0.0

# New for Ollama (optional, for direct API)
# ollama ^0.1.0  # Only if not using OpenAI-compatible API

# Remove (not used)
numpy ^1.26.4  # Not used in current code
pandas ^2.2.2  # Not used in current code
scikit-learn ^1.4.2  # Not used in current code
```

### Dependency Direction Validation
**Current:** ✅ CORRECT
- No circular dependencies
- Proper layering (controller → service → utility)

**After Refactor:** ✅ WILL REMAIN CORRECT
- New abstractions maintain proper layering
- Factory pattern maintains dependency direction
- No circular dependencies introduced

---

## Configuration Architecture

### Current Configuration Issues
1. **No Validation:** Environment variables read without validation
2. **No Defaults:** Some variables lack sensible defaults
3. **No Documentation:** .env.dist lacks explanations
4. **No Type Safety:** String values only, no type checking
5. **No Grouping:** Related variables not grouped logically

### Recommended Configuration Architecture

**Configuration File Structure:**
```python
# src/config.py
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class AIConfig(BaseSettings):
    provider: str = "openai"
    openai_api_key: str = ""
    openai_api_url: str = "https://api.openai.com/v1/"
    openai_model: str = "gpt-4-turbo"
    ollama_api_url: str = "http://localhost:11434/v1/"
    ollama_model: str = "dolphin-mixtral:latest"
    ollama_timeout: int = 300
    
    class Config:
        env_prefix = "AI_"

class EmailConfig(BaseSettings):
    provider: str = "generic"
    imap_host: str = ""
    imap_port: int = 993
    imap_use_ssl: bool = True
    email_username: str = ""
    email_password: str = ""
    gmail_username: str = ""
    gmail_app_password: str = ""
    yahoo_username: str = ""
    yahoo_app_password: str = ""
    folder_prefix: str = "AI-"
    
    class Config:
        env_prefix = "EMAIL_"

class AppConfig(BaseSettings):
    dry_run: bool = False
    show_prompt: bool = False
    limit: int = None
    
    class Config:
        env_prefix = "APP_"

class Config(BaseModel):
    ai: AIConfig = Field(default_factory=AIConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    
    @classmethod
    def load(cls) -> "Config":
        return cls(
            ai=AIConfig(),
            email=EmailConfig(),
            app=AppConfig()
        )
```

**Benefits:**
- ✅ Type-safe configuration
- ✅ Validation at startup
- ✅ Sensible defaults
- ✅ Environment variable prefixing
- ✅ Easy to test
- ✅ Self-documenting

---

## Redis Architecture Assessment

**Current State:** No Redis usage
**Assessment:** Not applicable for current architecture
**Recommendation:** Redis not needed for current scope, but consider for:
- Caching AI classifications for similar emails
- Rate limiting for API calls
- Session state for future web UI

---

## Streamlit Architecture Assessment

**Current State:** No Streamlit usage
**Assessment:** Not applicable for current architecture
**Recommendation:** Streamlit not in current scope, but consider for:
- Web-based configuration UI
- Real-time monitoring of email processing
- Visualization of classification results

---

## Refactor Recommendations

### Priority 1: Critical (Must Do Before New Features)

1. **Create Configuration Management**
   - File: `src/config.py`
   - Implement Pydantic configuration models
   - Add configuration validation
   - Update `.env.dist` with new variables

2. **Remove Code Duplication**
   - Remove duplicate functions from `ai.py`
   - Keep all utilities in `util.py`
   - Add imports where needed

3. **Implement AI Client Abstraction**
   - Create `src/ai/` package
   - Define `AIClient` interface
   - Move OpenAI logic to `openai_client.py`
   - Create client factory

### Priority 2: High (Should Do With New Features)

4. **Implement Email Provider Abstraction**
   - Create `src/email/` package
   - Define `EmailProvider` interface
   - Move generic IMAP to `generic_imap.py`
   - Create provider factory

5. **Add Data Models**
   - Create `src/models/` package
   - Define Pydantic models for Email, ClassificationResult
   - Update code to use models instead of dicts

6. **Implement Proper Logging**
   - Replace print statements with logging
   - Add log levels
   - Configure structured logging

### Priority 3: Medium (Nice to Have)

7. **Add Error Handling Hierarchy**
   - Create custom exception classes
   - Implement consistent error handling
   - Add error recovery logic

8. **Add Health Checks**
   - Implement AI service health check
   - Implement email provider health check
   - Add startup validation

9. **Add Retry Logic**
   - Implement exponential backoff
   - Add retry for network operations
   - Configure retry limits

### Priority 4: Low (Future Enhancements)

10. **Add Telemetry**
    - Implement metrics collection
    - Add performance monitoring
    - Track classification accuracy

11. **Add Connection Pooling**
    - Implement IMAP connection pool
    - Add connection reuse
    - Configure pool size

12. **Add Caching**
    - Consider Redis for classification cache
    - Cache folder listings
    - Cache provider configurations

---

## Implementation Risk Assessment

### High Risk Areas

1. **AI Client Migration**
   - **Risk:** Breaking existing OpenAI functionality
   - **Mitigation:** Keep `ai.py` as compatibility shim during migration
   - **Testing:** Comprehensive integration tests with OpenAI

2. **Email Provider Migration**
   - **Risk:** Breaking existing IMAP functionality
   - **Mitigation:** Keep `email_fetcher.py` as compatibility shim
   - **Testing:** Comprehensive integration tests with real IMAP servers

3. **Configuration Changes**
   - **Risk:** Breaking existing user configurations
   - **Mitigation:** Support old environment variable names with deprecation warnings
   - **Testing:** Configuration migration tests

### Medium Risk Areas

4. **Gmail/Yahoo Specifics**
   - **Risk:** Provider-specific quirks not discovered until testing
   - **Mitigation:** Early testing with real accounts
   - **Testing:** Provider-specific integration tests

5. **Ollama Integration**
   - **Risk:** Ollama API compatibility issues
   - **Mitigation:** Use OpenAI-compatible API mode
   - **Testing:** Local Ollama instance testing

### Low Risk Areas

6. **Utility Refactoring**
   - **Risk:** Low - pure functions
   - **Mitigation:** Comprehensive unit tests
   - **Testing:** Unit tests for all utility functions

7. **Data Model Introduction**
   - **Risk:** Low - additive change
   - **Mitigation:** Gradual migration from dicts to models
   - **Testing:** Model validation tests

---

## Testing Architecture Recommendations

### Test Structure
```
tests/
├── unit/
│   ├── test_ai/
│   ├── test_email/
│   ├── test_models/
│   └── test_util/
├── integration/
│   ├── test_ai_integration/
│   ├── test_email_integration/
│   └── test_end_to_end/
└── fixtures/
    ├── sample_emails/
    └── mock_responses/
```

### Testing Strategy

**Unit Tests:**
- Test each client/provider in isolation
- Mock external dependencies (OpenAI API, IMAP servers)
- Test configuration validation
- Test utility functions

**Integration Tests:**
- Test AI clients with mock servers
- Test email providers with test IMAP accounts
- Test factory patterns
- Test error handling

**End-to-End Tests:**
- Test full email processing pipeline
- Test with JSON fetcher (no external dependencies)
- Test configuration loading
- Test CLI argument parsing

### Mocking Strategy

**AI Mocking:**
- Mock OpenAI API responses
- Mock Ollama API responses
- Use pytest-mock for function mocking
- Use responses library for HTTP mocking

**Email Mocking:**
- Mock IMAPClient library
- Use test IMAP server (GreenMail)
- Use JSON fetcher for deterministic testing
- Mock network errors

---

## Security Architecture Considerations

### Current Security Issues

1. **Credential Storage**
   - **Issue:** Credentials in environment variables
   - **Risk:** Environment variable leakage
   - **Recommendation:** Consider key management service for production

2. **No Input Validation**
   - **Issue:** No validation of email content
   - **Risk:** Potential injection attacks
   - **Recommendation:** Add input sanitization

3. **No Rate Limiting**
   - **Issue:** No client-side rate limiting
   - **Risk:** API abuse, cost overruns
   - **Recommendation:** Implement rate limiting

4. **No Audit Logging**
   - **Issue:** No logging of sensitive operations
   - **Risk:** No audit trail
   - **Recommendation:** Add audit logging for email moves

### Recommended Security Enhancements

1. **Credential Validation**
   - Validate credentials at startup
   - Test connectivity before processing
   - Fail fast on invalid credentials

2. **Input Sanitization**
   - Sanitize email content before processing
   - Validate folder names
   - Escape special characters

3. **Rate Limiting**
   - Implement token bucket rate limiting
   - Configure per-provider limits
   - Monitor usage

4. **Audit Logging**
   - Log all email moves
   - Log AI classifications
   - Log configuration changes

---

## Performance Considerations

### Current Performance Characteristics

- **Sequential Processing:** One email at a time
- **No Caching:** Every email requires AI call
- **No Batching:** Single email per API call
- **No Connection Pooling:** Single IMAP connection

### Recommended Performance Enhancements

1. **Batch Processing**
   - Process multiple emails in parallel
   - Use async/await for I/O operations
   - Configure batch size

2. **Caching**
   - Cache AI classifications for similar emails
   - Cache folder listings
   - Use Redis for distributed caching

3. **Connection Pooling**
   - Pool IMAP connections
   - Reuse HTTP connections for AI API
   - Configure pool sizes

4. **Async Processing**
   - Use asyncio for concurrent operations
   - Implement async AI clients
   - Implement async email providers

---

## Migration Strategy

### Phase 1: Foundation (Week 1)
1. Create configuration management
2. Remove code duplication
3. Add data models
4. Implement proper logging
5. Add basic tests

### Phase 2: AI Layer (Week 2)
1. Create AI client abstraction
2. Implement OpenAI client
3. Implement Ollama client
4. Create client factory
5. Add AI tests
6. Update main.py to use factory

### Phase 3: Email Layer (Week 3)
1. Create email provider abstraction
2. Implement generic IMAP provider
3. Implement Gmail provider
4. Implement Yahoo provider
5. Create provider factory
6. Add email tests
7. Update main.py to use factory

### Phase 4: Integration (Week 4)
1. Update configuration files
2. Update documentation
3. Add integration tests
4. Performance testing
5. Security review
6. Code review

### Phase 5: Deployment (Week 5)
1. Beta testing with real users
2. Bug fixes
3. Performance tuning
4. Documentation updates
5. Release preparation

---

## Conclusion

The Sort Buddy application has a solid foundation but requires architectural refactoring to support the proposed Ollama and multi-provider IMAP features cleanly. The current architecture is functional but lacks the abstraction layers needed for maintainable extensibility.

**Key Takeaways:**
1. ✅ Current dependency graph is correct and clean
2. ⚠️ Lack of abstraction layers for AI and email providers
3. ⚠️ No configuration management or validation
4. ⚠️ Code duplication and hard-coded values
5. ⚠️ No testing infrastructure
6. ⚠️ Inconsistent error handling and logging

**Recommended Path Forward:**
1. Implement configuration management with Pydantic
2. Create AI client abstraction layer
3. Create email provider abstraction layer
4. Add comprehensive testing
5. Migrate existing code to new abstractions
6. Implement Ollama and Gmail/Yahoo providers

**Overall Assessment:** The architecture is **NEEDS_REFACTOR** but the refactoring is straightforward and will significantly improve the codebase's maintainability and extensibility. The proposed changes are well-scoped and can be implemented incrementally without disrupting existing functionality.

---

## Appendix: File-by-File Analysis

### src/main.py
- **Lines:** 114
- **Responsibility:** Controller/orchestration
- **Issues:** Contains business logic (folder validation)
- **Recommendation:** Move folder validation to service layer

### src/ai.py
- **Lines:** 100
- **Responsibility:** AI service layer
- **Issues:** Tight coupling to OpenAI, code duplication
- **Recommendation:** Refactor into abstraction layer

### src/email_fetcher.py
- **Lines:** 102
- **Responsibility:** Email data access
- **Issues:** No provider abstraction
- **Recommendation:** Refactor into provider pattern

### src/json_email_fetcher.py
- **Lines:** 41
- **Responsibility:** Mock data access
- **Issues:** None - good pattern
- **Recommendation:** Keep as-is, add interface

### src/util.py
- **Lines:** 46
- **Responsibility:** Shared utilities
- **Issues:** Some functions duplicated in ai.py
- **Recommendation:** Remove duplicates, add tests

### tests/__init__.py
- **Lines:** 0
- **Responsibility:** Test package
- **Issues:** Empty - no tests
- **Recommendation:** Implement comprehensive test suite

### .env.dist
- **Lines:** 15
- **Responsibility:** Configuration template
- **Issues:** Minimal, lacks documentation
- **Recommendation:** Expand with new variables and documentation

### pyproject.toml
- **Lines:** 25
- **Responsibility:** Dependency management
- **Issues:** Unused dependencies (numpy, pandas, scikit-learn)
- **Recommendation:** Remove unused, add testing dependencies

### README.md
- **Lines:** 69
- **Responsibility:** Documentation
- **Issues:** Outdated (mentions Ollama but not implemented)
- **Recommendation:** Update after implementation

---

**Review Complete**
**Status:** NEEDS_REFACTOR
**Confidence:** High
**Next Steps:** Proceed with planning phase
