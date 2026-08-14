# JSON Prompt Mode and Model Testing Plan

**Date:** 2025-01-14
**Planner:** planner agent
**Coordinator:** coordinator agent
**Branch:** feature/prompt-improvement

## Context

The sort-buddy email classifier uses Ollama's OpenAI-compatible endpoint to sort IMAP emails into AI-prefixed folders. The current implementation has three critical issues:

1. **Stale folder definitions:** `FOLDER_DEFINITIONS` in `src/ai/prompts.py` contains "Mailing-List" and "Work" entries that don't exist in the actual IMAP folders, and is missing "Notifications" and "Other" definitions. The actual IMAP folders are: `AI-Important`, `AI-Newsletters`, `AI-Notifications`, `AI-Other`, `AI-Personal`, `AI-Spam` (6 folders).

2. **Poor format compliance:** Local LLM models (qwen2.5:7b-instruct-q4_K_M, qwen3.5:4b, llama3.1:8b) consistently return long essays, multi-paragraph summaries, or rewritten email bodies instead of the required one-line `Folder: brief explanation` format. This causes many `invalid` classifications, especially on transactional/ambiguous emails (statements, alerts, saved-search notifications).

3. **Model fit issues:** The tested models either don't follow the format constraint or produce empty/malformed responses on certain email types. The user has an RTX 2060 6 GB GPU and needs a model that fits within this VRAM constraint while reliably following format instructions.

## Goals

1. **Update folder definitions:** Correct `FOLDER_DEFINITIONS` and `SYSTEM_PROMPT_TEMPLATE` to match the actual 6 IMAP folders with accurate definitions and examples.

2. **Implement JSON mode:** Add an optional JSON output mode to the Ollama client that requests structured output `{"folder": "...", "explanation": "..."}` using OpenAI's `response_format={"type": "json_object"}` or Ollama's `extra_body={"format": "json"}`. Keep the existing one-line text mode working as a fallback.

3. **Test a better model:** Pull and test a small instruction-tuned model that fits 6 GB VRAM (e.g., gemma3:4b, phi3:mini, or similar) and update `.env.dist` with the recommended model.

4. **Add comprehensive tests:** Update and add unit tests for the new prompt definitions, JSON parsing, and JSON mode client behavior.

5. **Follow verification pipeline:** Execute the coordinator verification pipeline: python-developer → testing-guardian → ollama-specialist → qa-ci-agent → python-reviewer.

## Impacted Components

- `src/ai/prompts.py` — Update `FOLDER_DEFINITIONS`, `SYSTEM_PROMPT_TEMPLATE`, add JSON prompt variant, add `parse_json_classification` function
- `src/ai/ollama_client.py` — Add optional JSON mode parameter, implement `response_format` or `extra_body` support, add JSON parsing fallback
- `src/ai/base.py` — Update `classify_email` signature to include `use_json_mode` parameter (optional, default False)
- `src/ai/openai_client.py` — Update to support `use_json_mode` parameter for consistency (no-op if not needed)
- `.env.dist` — Update `LLM_MODEL` recommendation with tested model
- `tests/unit/test_ai/test_prompts.py` — Add tests for new folder definitions, JSON prompt generation, JSON parsing
- `tests/unit/test_ai/test_ollama_client.py` — Add tests for JSON mode, mock JSON responses, fallback behavior
- `src/config.py` — Add optional `LLM_USE_JSON_MODE` configuration flag (optional, can be CLI flag instead)

## Non-Goals

- Do not modify the IMAP folder structure or email provider logic
- Do not change the existing one-line text mode (add JSON as optional enhancement)
- Do not modify the multi-account configuration
- Do not add OAuth2 or other authentication changes
- Do not change the base OpenAI client behavior beyond signature consistency

## Waves

### Wave 1: Update Folder Definitions and Prompts (python-developer)

**Agent:** python-developer
**Files:** `src/ai/prompts.py`
**Description:**
- Update `FOLDER_DEFINITIONS` to match the 6 actual folders:
  - `Important`: Genuinely time-sensitive or personal mail that requires prompt attention
  - `Newsletters`: Marketing, promotions, newsletters, coupons, and recurring mass mail
  - `Notifications`: Automated alerts, statements, receipts, and account updates from services
  - `Other`: Anything that does not match the other categories
  - `Personal`: Private, non-work, or individually addressed messages
  - `Spam`: Unwanted, unsolicited, or suspicious bulk mail
- Remove stale "Mailing-List" and "Work" entries
- Update `SYSTEM_PROMPT_TEMPLATE` to:
  - List all 6 folders with their definitions
  - Add explicit examples for each folder type
  - Strengthen the format constraint with multiple examples
  - Add negative examples (what NOT to do)
- Add a new `SYSTEM_PROMPT_JSON_TEMPLATE` for JSON mode that instructs the model to output `{"folder": "...", "explanation": "..."}`
- Add `generate_json_prompt()` function that builds prompts for JSON mode
- Add `parse_json_classification(content: str, folders: list[str]) -> tuple[str, str]` function to parse JSON responses with fallback to text parsing

**Acceptance criteria:**
- `FOLDER_DEFINITIONS` contains exactly 6 entries matching the actual IMAP folders
- `SYSTEM_PROMPT_TEMPLATE` includes all 6 folders with definitions and examples
- `SYSTEM_PROMPT_JSON_TEMPLATE` exists and instructs JSON output format
- `generate_json_prompt()` returns system and user prompts for JSON mode
- `parse_json_classification()` parses valid JSON and returns (folder, explanation)
- `parse_json_classification()` falls back to text parsing on invalid JSON

**Verification:** python-reviewer

---

### Wave 2: Implement JSON Mode in Ollama Client (python-developer)

**Agent:** python-developer
**Files:** `src/ai/ollama_client.py`, `src/ai/base.py`, `src/ai/openai_client.py`
**Description:**
- Update `AIClient.classify_email()` signature in `src/ai/base.py` to add optional `use_json_mode: bool = False` parameter
- Update `OllamaClient.classify_email()` to:
  - Accept `use_json_mode` parameter
  - When `use_json_mode=True`, use `generate_json_prompt()` instead of `generate_prompt()`
  - Add `response_format={"type": "json_object"}` to the OpenAI client call (Ollama supports this)
  - Alternatively, try `extra_body={"format": "json"}` if response_format is not supported
  - Parse response using `parse_json_classification()` when in JSON mode
  - Fall back to text mode parsing if JSON parsing fails
- Update `OpenAIClient.classify_email()` to accept `use_json_mode` parameter for consistency (can be no-op or implement if desired)
- Add error handling for JSON mode failures (fallback to text mode with warning)

**Acceptance criteria:**
- `AIClient.classify_email()` signature includes `use_json_mode: bool = False`
- `OllamaClient.classify_email()` accepts and uses `use_json_mode` parameter
- When `use_json_mode=True`, the client uses `response_format={"type": "json_object"}` or `extra_body={"format": "json"}`
- JSON responses are parsed correctly and return (folder, explanation)
- Invalid JSON responses fall back to text parsing
- Text mode (use_json_mode=False) continues to work as before

**Verification:** ollama-specialist, python-reviewer

---

### Wave 3: Update Unit Tests for Prompts (testing-guardian)

**Agent:** testing-guardian
**Files:** `tests/unit/test_ai/test_prompts.py`
**Description:**
- Update existing `test_generate_prompt_includes_folders` to check for all 6 folders
- Add `test_folder_definitions_has_all_six_folders()` to verify FOLDER_DEFINITIONS completeness
- Add `test_generate_json_prompt_includes_folders()` for JSON prompt generation
- Add `test_parse_json_classification_valid()` for valid JSON parsing
- Add `test_parse_json_classification_invalid_json_fallback()` for fallback behavior
- Add `test_parse_json_classification_missing_fields()` for malformed JSON
- Update existing `parse_classification` tests to cover the new folder names
- Add tests for negative examples (marketing emails should not classify as Important)

**Acceptance criteria:**
- All existing tests pass
- New tests verify 6 folder definitions are present
- JSON prompt generation tests pass
- JSON parsing tests cover valid, invalid, and malformed cases
- Test coverage for `src/ai/prompts.py` remains above 80%

**Verification:** qa-ci-agent

---

### Wave 4: Update Unit Tests for Ollama Client (testing-guardian)

**Agent:** testing-guardian
**Files:** `tests/unit/test_ai/test_ollama_client.py`
**Description:**
- Add `test_classify_email_json_mode_valid()` mocking a valid JSON response
- Add `test_classify_email_json_mode_invalid_json_fallback()` mocking invalid JSON
- Add `test_classify_email_json_mode_uses_response_format()` to verify response_format parameter
- Add `test_classify_email_text_mode_still_works()` to ensure backward compatibility
- Update existing tests to verify they still pass with signature changes
- Add test for `extra_body={"format": "json"}` if implemented as alternative

**Acceptance criteria:**
- All existing tests pass
- JSON mode tests verify correct parameter passing and parsing
- Fallback behavior tests pass
- Text mode tests continue to pass
- Test coverage for `src/ai/ollama_client.py` remains above 80%

**Verification:** qa-ci-agent

---

### Wave 5: Pull and Test Small Model (ollama-specialist)

**Agent:** ollama-specialist
**Files:** `.env.dist`, documentation updates
**Description:**
- Research and select a small instruction-tuned model that fits 6 GB VRAM (candidates: gemma3:4b, phi3:mini, tinyllama, or similar)
- Pull the selected model using `ollama pull <model>`
- Test the model with both text mode and JSON mode using real transactional/ambiguous emails
- Compare results against current models (qwen2.5:7b, llama3.1:8b)
- Document VRAM usage and inference speed
- Update `.env.dist` with the recommended `LLM_MODEL` value and comments
- If no suitable local model is found, document the recommendation to use OpenAI gpt-4o-mini

**Acceptance criteria:**
- A model is pulled and tested on the RTX 2060 6 GB
- Model fits within VRAM constraint (monitor with `nvidia-smi`)
- Model follows format constraints better than current models
- `.env.dist` is updated with recommended model and comments
- Test results are documented (format compliance rate, VRAM usage, speed)

**Verification:** python-reviewer, qa-ci-agent

---

### Wave 6: Integration Testing and Dry-Run (coordinator)

**Agent:** coordinator (orchestrates testing-guardian)
**Files:** None (integration testing)
**Description:**
- Run full test suite: `poetry run pytest`
- Run with coverage: `poetry run pytest --cov=src --cov-report=term-missing`
- Run type checking: `poetry run mypy src`
- Perform a dry-run with real emails: `poetry run python src/main.py --dry-run --limit 5 --show-prompt`
- Test both text mode and JSON mode (if CLI flag added, or via code change)
- Verify classification accuracy on transactional/ambiguous emails
- Check that no `invalid` classifications are caused by format issues

**Acceptance criteria:**
- All unit tests pass
- Test coverage remains above 80% for modified modules
- No new type errors introduced
- Dry-run processes emails without errors
- Classification format is correct (either `Folder: explanation` or JSON)
- Transactional/ambiguous emails are classified correctly

**Verification:** qa-ci-agent, python-reviewer

---

### Wave 7: Git Workflow (git-workflow)

**Agent:** git-workflow
**Files:** Git history
**Description:**
- Stage all changes
- Create a commit with message: "feat: add JSON mode and update folder definitions for better LLM compliance"
- Commit message should include:
  - Summary of changes (folder definitions, JSON mode, model recommendation)
  - Reference to this plan file
  - Attribution to Devin
- Do NOT push (wait for human review)

**Acceptance criteria:**
- All changes are committed
- Commit message follows conventional commit format
- Commit includes attribution to Devin
- No uncommitted changes remain

**Verification:** coordinator

---

## Verification Pipeline

After all waves are complete, execute the following verification sequence:

1. **swe-check** — Review non-Python artifacts (config changes, .env.dist updates)
2. **testing-guardian** — Run full test suite with coverage
3. **security-auditor** — Scan for any secrets or security issues in new code
4. **python-reviewer** — Code review of all Python changes (prompts.py, ollama_client.py, base.py, openai_client.py)
5. **ollama-specialist** — Review Ollama integration and JSON mode implementation
6. **qa-ci-agent** — Ensure CI workflows, linting, type checking are green
7. **coordinator** — Final review and human approval before merge

## Acceptance Criteria (Overall)

- [ ] FOLDER_DEFINITIONS matches the 6 actual IMAP folders exactly
- [ ] SYSTEM_PROMPT_TEMPLATE includes all 6 folders with accurate definitions
- [ ] JSON mode is implemented and functional in OllamaClient
- [ ] JSON parsing works with fallback to text mode
- [ ] Text mode continues to work as before (backward compatibility)
- [ ] Unit tests cover new functionality (JSON mode, new folder definitions)
- [ ] Test coverage remains above 80% for modified modules
- [ ] A suitable model is tested and recommended in .env.dist
- [ ] Dry-run with real emails succeeds without format-related `invalid` classifications
- [ ] All verification agents pass (swe-check, testing-guardian, security-auditor, python-reviewer, ollama-specialist, qa-ci-agent)
- [ ] Changes are committed with proper message and Devin attribution
- [ ] Human review is completed before merge

## Open Questions

1. **JSON mode activation:** Should JSON mode be activated via:
   - Environment variable (`LLM_USE_JSON_MODE=true`)
   - CLI flag (`--use-json-mode`)
   - Automatic detection (try JSON first, fall back to text)
   - Configuration in accounts.yaml
   - *Decision to be made by python-developer based on use case*

2. **Model selection:** Which small model should be recommended?
   - gemma3:4b (Google, ~2-3 GB VRAM)
   - phi3:mini (Microsoft, ~2 GB VRAM)
   - tinyllama (community, ~1 GB VRAM)
   - Other candidate?
   - *Decision to be made by ollama-specialist after testing*

3. **Response format support:** Does the Ollama instance at http://192.168.0.116:11434/v1/ support OpenAI's `response_format={"type": "json_object"}` or should we use Ollama's native `extra_body={"format": "json"}`?
   - *Decision to be made by ollama-specialist during implementation*

4. **CLI flag needed:** Should we add a `--use-json-mode` CLI flag to main.py for easy testing, or rely solely on environment variables?
   - *Decision to be made by python-developer*

## Dependencies

- Ollama instance must be running at http://192.168.0.116:11434/v1/ for model testing
- GPU with 6 GB VRAM must be available for model testing
- Python 3.10+ environment with Poetry dependencies installed
- Test email data (either real IMAP access or JSON mock file) for dry-run testing

## Risk Assessment

- **Low risk:** Updating folder definitions and prompts (pure text changes)
- **Medium risk:** Adding JSON mode to client (requires careful error handling and fallback)
- **Medium risk:** Model testing (may require multiple iterations to find suitable model)
- **Low risk:** Unit test updates (well-understood test patterns)
- **Overall risk:** Medium — changes are localized to AI layer with fallback mechanisms

## Time Budget

- Wave 1 (prompts): 60-90 minutes
- Wave 2 (JSON mode): 90-120 minutes
- Wave 3 (prompt tests): 60-90 minutes
- Wave 4 (client tests): 60-90 minutes
- Wave 5 (model testing): 120-180 minutes (includes pull, test, compare)
- Wave 6 (integration): 60-90 minutes
- Wave 7 (git workflow): 30 minutes
- **Total:** 540-690 minutes (9-11.5 hours)

## Success Metrics

- Format compliance rate: >90% of responses should be parseable (either text or JSON)
- Classification accuracy: Transactional/ambiguous emails should be correctly classified (not marked as `invalid` due to format)
- VRAM usage: Selected model must fit within 6 GB VRAM with headroom
- Test coverage: >80% for modified modules
- Backward compatibility: Text mode must continue to work without regression
