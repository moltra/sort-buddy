# Few-Shot Prompt Improvement Plan

## Context
The rewritten prompt in `src/ai/prompts.py` is correctly classifying obvious
spam and newsletters, but `qwen2.5:7b-instruct-q4_K_M` is still rewriting or
summarizing the email body instead of producing the required
`Folder: brief explanation` format for transactional/ambiguous messages.

## Goal
Add a small set of in-prompt examples (few-shot) that show the model exactly
the desired `Folder: brief explanation` output for representative email types.

## Impacted Files
- `src/ai/prompts.py`

## Implementation Notes
- Keep the existing `SYSTEM_PROMPT_TEMPLATE` rules and folder definitions.
- Append a "Examples" section with 3-4 examples:
  1. Newsletter: `Newsletters: This is a regular industry newsletter with multiple article links and a sponsor section.`
  2. Notification: `Notifications: This is an automated statement or account alert from a service the recipient uses.`
  3. Spam: `Spam: This is an unsolicited promotional message with suspicious links and excessive discount claims.`
  4. Important: `Important: This is a personal or time-sensitive message from a known contact that requires prompt attention.`
- Examples must use the stripped folder names the app will see (e.g., `Newsletters`, `Notifications`, `Spam`, `Important`).
- Keep examples short so the prompt stays within context limits.

## Acceptance Criteria
- [ ] `poetry run pytest tests/unit/test_ai/test_prompts.py` passes.
- [ ] The new prompt still works for the known good spam/newsletter cases.
- [ ] A `--dry-run --limit 3` on the current inbox produces `Folder: explanation`
      output for at least the previously-failing transactional messages.
