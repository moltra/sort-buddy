# LLM Research Request for sort-buddy

## Paste this into ChatGPT / Claude / Perplexity / etc.

I have a Python email classifier called **sort-buddy**. It uses an
Ollama OpenAI-compatible endpoint (`/v1/chat/completions`) to sort IMAP
emails into folders.

### Hardware
- GPU: NVIDIA RTX 2060 6 GB
- Host RAM: 32 GB
- Ollama runs on the same machine (default `http://localhost:11434/v1/`)

### Constraints
- Must be a **local Ollama model** that fits in 6 GB VRAM.
- Must be available from the Ollama library (or easy to pull via `ollama pull`).
- Should respond to a simple one-line `Folder: brief explanation` prompt.

### Current system prompt

```
You are an email classifier. Pick exactly one folder for the email below.

Available folders:
- Important: Genuinely time-sensitive or personal mail that requires prompt attention.
- Spam: Unwanted, unsolicited, or suspicious bulk mail.
- Newsletters: Marketing, promotions, newsletters, coupons, and recurring mass mail.
- Notifications: Automated alerts, statements, receipts, and account updates.
- Other: Anything that does not match the other categories.
- Personal: Private, non-work, or individually addressed messages.

Use Inbox only when the email is too ambiguous to classify.

Rules:
- Respond with exactly this format and nothing else: <Folder>: <brief explanation>
- Do not include introductions, conclusions, code blocks, quotes, or extra lines.
- Marketing, promotions, newsletters, coupons, and unsolicited mass mail belong in Newsletters or Spam, never in Important.
- Important is only for genuinely time-sensitive or personal mail.
- If none of the folders clearly fit and the email is not ambiguous, choose Inbox.
- Do NOT rewrite or summarize the email body.

Examples (respond with exactly one line like these):
Newsletters: This is a regular industry newsletter with multiple article links and a sponsor section.
Notifications: This is an automated statement or account alert from a service the recipient uses.
Spam: This is an unsolicited promotional message with suspicious links and excessive discount claims.
Important: This is a personal or time-sensitive message from a known contact that requires prompt attention.
```

The user prompt is:

```
Email Subject: <subject>
Email From: <from>
Email Body: <body>
```

### Models already tested

| Model | Size | Result |
|-------|------|--------|
| `qwen2.5:7b-instruct-q4_K_M` | ~4.7 GB | Works for obvious Spam and Newsletters, but rewrites/summarizes transactional emails (e.g., statements, saved-search alerts) instead of outputting `Folder: explanation`. |
| `qwen3.5:4b` | ~3.4 GB | Produced empty/malformed responses for statements. |
| `llama3.1:8b` (default Ollama q4_0) | ~4.7 GB | Works for Spam, but either returns no colon (`could not split response`) or summarizes statements without choosing a folder. |

### What I need

1. Recommend a **better Ollama model** for this exact task that fits in 6 GB VRAM.
2. If you think I should change the prompt strategy (e.g., move all instructions into the user message, use `### Response:`, JSON mode, Ollama `format: json`, etc.), say so and give the exact revised prompt.
3. If a small-cloud API like OpenAI `gpt-4o-mini` is genuinely the only reliable option, say that too.

### Bonus points
- Include the exact `ollama pull` command.
- Include the exact `LLM_MODEL` value to put in `.env`.
- Mention expected VRAM usage and inference speed on an RTX 2060.

---

## Human summary (for the sort-buddy team)

The local 7-8B instruction-tuned models we have tried all refuse to stick to
the one-line `Folder: explanation` format when the email body is long or
ambiguous. We need a recommendation for a more reliable Ollama model or a
better prompt/constrain strategy for this constrained-output classification
task on a 6 GB RTX 2060.
