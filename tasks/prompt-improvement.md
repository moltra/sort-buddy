# Prompt Improvement Plan

## Context
The current system prompt in `src/ai/prompts.py` is too generic. The local
`qwen2.5:7b-instruct-q4_K_M` model (4.7 GB, fits the user's 6 GB RTX 2060)
produces long essays, multi-paragraph summaries, or chooses `Important` for
obvious marketing/promotional mail. This results in many `invalid`
classifications and mis-sorted messages (e.g., spam/promos landing in
`AI-Important`).

## Goals
1. Make the system prompt explicit about the intended use of each
   `AI-*` folder and the `Inbox` fallback.
2. Force the model to output exactly `Folder: brief explanation` with no
   surrounding text.
3. Harden `parse_classification` to tolerate common model deviations such as
   extra whitespace, surrounding quotes, or multi-line replies.
4. Keep the changes scoped to `src/ai/prompts.py` and the relevant unit tests.

## Impacted Files
- `src/ai/prompts.py` (system prompt, parser)
- `tests/unit/test_ai/test_prompts.py` (test updates and new cases)

## Non-Goals
- Do not modify `src/ai/openai_client.py` or `src/ai/ollama_client.py`.
- Do not touch `.env`, `.env.dist`, or account configuration.
- Do not add, remove, or rename AI folders.
- Do not fine-tune or change the model itself.

## Waves

### Wave 1: Prompt and Parser (python-developer)
- Owner: `src/ai/prompts.py`
- Rewrite `SYSTEM_PROMPT_TEMPLATE` to:
  - List every available `AI-*` folder by its short name.
  - Provide a one-sentence definition for each folder.
  - State clearly that marketing, promotions, newsletters, and unsolicited
    mass mail belong in `Newsletters` or `Spam`, not `Important`.
  - Explain that `Important` is for genuinely time-sensitive or personal mail.
  - Use `Inbox` only when the email is too ambiguous to classify.
  - Instruct the model to respond with **exactly** `Folder: brief explanation`
    and nothing else.
- Harden `parse_classification`:
  - Split on the first colon and consider only the first line if the model
    returns multiple lines.
  - Strip surrounding quotes or backticks from the folder name.
  - Treat `folder not in folders` as `invalid` as before, but normalize the
    extracted folder name first.

### Wave 2: Unit Tests (testing-guardian)
- Owner: `tests/unit/test_ai/test_prompts.py`
- Update existing `generate_prompt` tests for the new prompt text.
- Add `parse_classification` tests for:
  - Multi-line essay response (must pick first line/folder).
  - Folder wrapped in quotes or backticks.
  - Marketing content producing `Newsletters` or `Spam`.
  - Unknown folder still returns `invalid`.

### Wave 3: Verification (qa-ci-agent / coordinator)
- `poetry run pytest tests/unit/test_ai/test_prompts.py`
- `poetry run pytest`
- `poetry run mypy src` (note: `src/ai` is currently ignored by mypy)
- `poetry run python src/main.py --dry-run --limit 3` once unit tests pass
- Git commit each wave separately

## Acceptance Criteria
- [ ] `poetry run pytest tests/unit/test_ai/test_prompts.py` passes.
- [ ] `poetry run pytest` passes.
- [ ] No new type errors in `src/ai/prompts.py` (mypy currently ignores `ai`).
- [ ] A dry-run on at least 3 real emails yields `Folder: explanation` format
      for the majority and no `invalid` caused by formatting.
- [ ] Promotional/spam-like test inputs no longer resolve to `Important`.
