# Ollama + IMAP Enhancement — Coordination Task

**Branch:** `feature/ollama-imap-integration`
**Created:** 2026-08-12

## Context

Sort Buddy is an AI-powered email classifier that currently connects to a generic IMAP server and calls the OpenAI chat completions API. The goal is to extend the app so it can:

1. Use an Ollama instance that exposes the OpenAI-compatible API.
2. Connect to IMAP accounts, specifically Gmail and Yahoo Mail (in addition to any generic IMAP host).

The implementation must not be started by the coordinator. First, specialist sub-agents will perform a full review, then the `planner` sub-agent will create the detailed implementation plan.

## Goals

1. Obtain a full, parallel review of the existing codebase from architecture, Python quality, security, Ollama integration, and testing perspectives.
2. Integrate the review outputs.
3. Have the `planner` sub-agent produce a complete, actionable implementation plan (`PLAN.md`) and supporting task files.

## Subtasks

1. **Architecture Review** — `architecture-reviewer`
   - Scope: module boundaries, dependency graph, file ownership, structural consistency.
   - Deliverable: `.devin/reviews/ollama-imap-architecture.md`

2. **Python Code Review** — `python-reviewer`
   - Scope: `src/*.py` for bugs, style, patterns, error handling, and maintainability.
   - Deliverable: `.devin/reviews/ollama-imap-python.md`

3. **Security Audit** — `security-auditor`
   - Scope: secret handling, IMAP credentials, API keys, injection risks, and input validation.
   - Deliverable: `.devin/reviews/ollama-imap-security.md`

4. **Ollama Integration Review** — `ollama-specialist`
   - Scope: existing OpenAI client usage in `src/ai.py` and how to make it work with Ollama's OpenAI-compatible endpoint.
   - Deliverable: `.devin/reviews/ollama-imap-ollama.md`

5. **Testing & Verification Review** — `testing-guardian`
   - Scope: existing tests, coverage, mocking strategy, and what tests are needed for IMAP and Ollama.
   - Deliverable: `.devin/reviews/ollama-imap-testing.md`

6. **Planning** — `planner`
   - Inputs: all five review files above, plus `src/`, `pyproject.toml`, `.env.dist`, `README.md`, `CODEMAP.md`, `ARCHITECTURE_REVIEW.md`.
   - Deliverable: a detailed implementation plan at `PLAN.md` (repo root), and if needed, `tasks/ollama-imap-implementation.md`.

## File/Directory Ownership

- Reviews: `.devin/reviews/ollama-imap-*.md` (each sub-agent owns its own file)
- Coordinator spec: `.devin/tasks/ollama-imap.md` (this file)
- Final plan: `PLAN.md` and `tasks/ollama-imap-implementation.md` (planner)

## Acceptance Criteria

- [ ] All five review files are produced and committed.
- [ ] The planner's `PLAN.md` includes: goals, file-level changes, new dependencies, environment variables, test strategy, and implementation waves.
- [ ] The plan specifically covers Ollama (OpenAI-compatible API) and IMAP for Gmail and Yahoo Mail.
- [ ] No feature code is implemented during the planning phase.
