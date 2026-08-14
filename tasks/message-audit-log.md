# Message Audit Log Plan

## Context
When sort-buddy runs over a large inbox, the user cannot tell which
message the Ollama model is currently classifying or which message was
last processed. The current `loguru` logger is configured only for
`stderr`, so long-running background invocations appear silent until they
finish (or hang).

## Goals
1. Add a persistent log line for every email classification: message id,
   from, subject, chosen folder, and brief explanation.
2. Add a persistent log line for every actual move (non-dry-run): message
   id and target folder.
3. Make it easy for the user to `tail` the log file during a run.
4. Keep the existing `stdout`/`stderr` output unchanged.

## Impacted Files
- `src/main.py` (single-account path)
- `src/account_processor.py` (multi-account path)

## Non-Goals
- Do not change the AI prompt or the parser.
- Do not change `.env`/`run.sh`.
- Do not add a new CLI flag unless necessary.

## Implementation Notes
- Use the existing `loguru` logger.
- Add a file sink in `main.py` (`sys.stdout` is already configured there).
- Use `~/.sort-buddy.log` as the log file so the repo stays clean.
- Log at `INFO` level.
- Single-account `main.py`:
  - After `get_ai_response_from_message`, log
    `message_id from subject folder explanation`.
  - In the non-dry-run move branch, log `message_id target_folder`.
- Multi-account `account_processor.py`:
  - Add equivalent log calls inside `process_account`.
- Ensure all extra `loguru` setup is idempotent (calling `main()` or
  `process_account()` multiple times in tests should not create duplicate
  sinks).

## Acceptance Criteria
- [ ] `poetry run pytest tests/unit/test_main.py` passes.
- [ ] `poetry run pytest tests/unit/test_account_processor.py` passes.
- [ ] `poetry run pytest` targeted tests for `main` and `account_processor`
      pass without new failures.
- [ ] A dry-run or live run on one email writes an `INFO` line to
      `~/.sort-buddy.log` with the message id and chosen folder.
