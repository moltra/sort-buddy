# Ollama Integration Review — Sort Buddy

**Scope:** Review how `src/ai.py` calls the OpenAI API and what is required to make it work cleanly with Ollama's OpenAI-compatible `/v1/chat/completions` endpoint.

## 1. Current OpenAI API usage in `src/ai.py`

- **Lines 4–6** — `configure_openai()` sets module-level state:
  ```python
  openai.api_key = os.getenv("OPENAI_API_KEY")
  openai.base_url = os.getenv("OPENAI_API_URL")
  ```
  This relies on the `openai` package's implicit default client, which makes testing and multi-provider support harder.
- **Lines 43–55** — The call is made through the default client with raw-response access so rate-limit headers can be printed:
  ```python
  response = openai.chat.completions.with_raw_response.create(
      model=os.environ.get("OPENAI_MODEL"),
      messages=[{"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}],
  )
  ```
- **Lines 58–70** — The code reads OpenAI-specific rate-limit headers (`x-ratelimit-*`) and prints them when `--print-rate-limits` is used.
- **Line 71** — `response.parse()` converts the raw response into a `ChatCompletion` object.
- **Line 73** — The final text is taken from `response.choices[0].message.content`.
- **Lines 75–77** — A bare `except Exception` prints the error and calls `exit()`, terminating the whole process on any API failure.

The prompt itself (lines 16–38) asks the model to respond with `Folder: explanation`, which is parsed with `message.split(': ', 1)` (lines 79–86). No JSON mode or structured output is used.

## 2. Changes needed to target an Ollama `/v1/chat/completions` endpoint

Ollama exposes an OpenAI-compatible chat endpoint at `<ollama-host>/v1/chat/completions`. To make Sort Buddy use it, only a handful of call parameters change:

| Parameter | OpenAI | Ollama |
|---|---|---|
| `base_url` | `https://api.openai.com/v1/` | `http://localhost:11434/v1/` (or the value of `OLLAMA_HOST` plus `/v1/`) |
| `api_key` | Real OpenAI key | Any non-empty placeholder (e.g. `ollama`). Ollama ignores the `Authorization` header unless you have explicitly configured authentication. |
| `model` | `gpt-4-turbo`, `gpt-4o`, etc. | An Ollama model tag such as `llama3.1:latest`, `dolphin-mixtral:latest`, etc. The model must already be pulled. |
| Extra headers | None special | None required. The endpoint accepts the same JSON payload the OpenAI client sends. |

Important practical notes:

- **Cold-start latency:** Ollama loads the model on the first request. A cold model can take 10–30 seconds (or longer on CPU). The default timeout in the `openai` client may be too short; set an explicit timeout of at least `60.0` seconds.
- **Model availability:** If the model is not pulled, Ollama returns a 404-style error. The code must surface this clearly instead of crashing.
- **Authentication:** Most local Ollama deployments have no authentication. The `openai` client still requires an `api_key`, so pass a dummy string.

## 3. Differences in response format, rate limits, and headers

- **Response body:** Ollama's `/v1/chat/completions` returns a JSON body that is compatible with OpenAI's chat completion object: `choices[0].message.content` works the same way. Fields such as `model`, `usage`, and `created` may differ slightly, but the code only depends on the message content and rate-limit headers.
- **Rate-limit headers:** Ollama does **not** return OpenAI-style `x-ratelimit-limit-*` / `x-ratelimit-remaining-*` headers. The current `show_rate_limits` block will print `None` for every value when running against Ollama. Rate limiting for local inference is instead a matter of GPU/CPU capacity and concurrent requests.
- **Other headers:** No Ollama-specific headers are required. The OpenAI client automatically sends `Authorization: Bearer <api_key>` and `Content-Type: application/json`, both of which Ollama accepts.
- **Streaming:** Ollama supports `stream=True` on the same endpoint. Sort Buddy currently does not stream, so this is not required for parity, but it is worth noting for future UI work.

## 4. `openai` Python client vs. plain HTTP client

**Recommendation: keep the `openai` Python client.**

Reasons:

- The project already depends on `openai = "^1.26.0"`.
- It handles request/response serialization, retries, timeouts, and typed parsing for the OpenAI-compatible protocol.
- Switching to a plain HTTP client (`requests`/`httpx`) would require re-implementing retries, JSON parsing, and header handling with no material benefit for `/v1/chat/completions`.
- A plain HTTP client only becomes worthwhile if Sort Buddy later needs Ollama-native endpoints such as `/api/generate`, `/api/embed`, or `/api/tags`. For chat completions, the OpenAI client is the pragmatic choice.

## 5. Recommended environment variables

Introduce provider-agnostic names and map the legacy OpenAI names as fallbacks:

| Variable | Purpose | Example |
|---|---|---|
| `LLM_PROVIDER` | Which backend to use: `openai` or `ollama`. | `ollama` |
| `LLM_BASE_URL` | Base URL for the chat endpoint. | `http://localhost:11434/v1/` or `https://api.openai.com/v1/` |
| `LLM_API_KEY` | API key or placeholder. | `ollama` or real OpenAI key |
| `LLM_MODEL` | Model name/tag. | `llama3.1:latest` or `gpt-4o` |
| `LLM_TIMEOUT` | Request timeout in seconds. | `60.0` |
| `OLLAMA_HOST` | Optional Ollama-specific host override. | `http://192.168.1.10:11434` |

Backward compatibility:

- If `LLM_PROVIDER` is missing, infer it from the existing `OPENAI_API_URL`/`OPENAI_MODEL` variables and default to `openai`.
- Map `OPENAI_API_URL` -> `LLM_BASE_URL`, `OPENAI_API_KEY` -> `LLM_API_KEY`, and `OPENAI_MODEL` -> `LLM_MODEL` when the provider is `openai`.
- This lets existing `.env` files continue to work while new Ollama deployments use the clearer `LLM_*` names.

## 6. How to support both OpenAI and Ollama with configuration

A small configuration object plus an explicit client instance is the cleanest approach:

1. Read `LLM_PROVIDER` (defaulting to `openai`).
2. Resolve `base_url`, `api_key`, `model`, and `timeout` from provider-specific env vars with sensible defaults.
3. Build an `openai.OpenAI(base_url=..., api_key=..., timeout=...)` instance.
4. Pass that client (or a thin wrapper) into `get_ai_response()` instead of relying on the module-level default client.
5. Make rate-limit printing conditional on `provider == "openai"` and on the presence of the relevant headers.
6. For Ollama, optionally check `/api/tags` before the first chat call or catch `openai.NotFoundError` and explain that the model may need to be pulled.

This keeps the OpenAI and Ollama code paths almost identical; only configuration and a few helper behaviors differ.

## 7. Specific code-level recommendations

1. **Stop using module-level `openai.api_key` / `openai.base_url`.**
   - Instantiate a client explicitly:
     ```python
     from openai import OpenAI

     client = OpenAI(base_url=config.base_url, api_key=config.api_key, timeout=config.timeout)
     ```
2. **Add an explicit timeout.**
   - Ollama cold starts can exceed default HTTPX timeouts. Use at least `60.0` seconds, ideally configurable via `LLM_TIMEOUT`.
3. **Replace `configure_openai()` with a provider-aware `configure_llm()`.**
   - Return a small config dataclass and/or the `OpenAI` client.
   - Example:
     ```python
     @dataclass
     class LLMConfig:
         provider: str
         base_url: str
         api_key: str
         model: str
         timeout: float
     ```
4. **Refactor `get_ai_response()` to accept the client or config as an argument.**
   - This enables dependency injection in tests and avoids global state.
5. **Handle Ollama-specific errors.**
   - Catch `openai.APIConnectionError` for "Ollama is not running".
   - Catch `openai.NotFoundError` for "model not found / not pulled".
   - Catch `openai.RateLimitError` and `openai.APIStatusError` as appropriate.
   - **Never call `exit()` inside library code.** Return an error tuple or raise a domain exception so callers can decide what to do.
6. **Make `show_rate_limits` provider-specific.**
   - For OpenAI, continue reading `x-ratelimit-*` headers.
   - For Ollama, either skip the output or print a note that local inference does not expose rate-limit headers.
7. **Validate the model before the first call (optional but helpful).**
   - For Ollama, a quick GET to `<base_url without /v1>/api/tags` (or use the Ollama Python SDK) can verify the model exists.
   - Alternatively, rely on the 404 error from the chat call and produce a clear message: e.g. "Model 'llama3.1:latest' not found. Run `ollama pull llama3.1:latest`."
8. **Improve the response parser.**
   - The current `split(': ', 1)` is brittle. Consider a small regex or JSON-mode fallback for local models that may add extra whitespace or reasoning text.
9. **Add tests with mocked clients.**
   - Patch `openai.OpenAI` or the client instance returned by `configure_llm()`.
   - Verify that no real HTTP request is made to `localhost:11434` during tests.
   - Test both OpenAI-style (with rate-limit headers) and Ollama-style (no headers) responses.
10. **Update `.env.dist` and `README.md`.**
    - `.env.dist` already has commented Ollama values; expand them to the new `LLM_*` variables.
    - `README.md` should explain that `LLM_PROVIDER=ollama`, `LLM_BASE_URL=http://localhost:11434/v1/`, and `LLM_MODEL=...` are the recommended settings for local models.

## 8. Issues found

| File | Line(s) | Severity | Issue |
|---|---|---|---|
| `src/ai.py` | 4–6 | warning | Uses module-level `openai.api_key`/`openai.base_url` instead of an explicit `OpenAI` client instance. |
| `src/ai.py` | 43 | warning | No explicit `timeout`, so Ollama cold-start requests may time out. |
| `src/ai.py` | 58–70 | info | Rate-limit header printing is OpenAI-specific and produces `None` values against Ollama. |
| `src/ai.py` | 75–77 | critical | Bare `except Exception` followed by `exit()` terminates the process and prevents callers from handling Ollama connection/model-not-found errors gracefully. |
| `src/ai.py` | 79–86 | warning | Response parsing relies on a single `: ` delimiter; local models are more likely to deviate from this format. |
| `src/main.py` | 59 | info | Hardcoded `model=os.getenv("OPENAI_MODEL")` ties runtime reporting to OpenAI-branded env vars. |
| `.env.dist` | 3–9 | info | Only OpenAI-branded variables exist; no provider-agnostic `LLM_*` settings. |
| `src/ai.py` | 1–100 | warning | No test isolation: tests would need to patch the implicit default client or module-level state. |

## 9. PASS/FAIL summary

- **Current state:** The existing code can already hit an Ollama `/v1/chat/completions` endpoint by setting the right `OPENAI_API_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` values, but it does so through brittle global state and without any Ollama-specific error handling.
- **Verdict:** **FAIL** for production-ready Ollama support because of the `exit()`-on-error behavior, missing timeouts, OpenAI-specific naming, and lack of test isolation.
- **Path to PASS:** Implement a provider-aware `LLMConfig`/`configure_llm()` wrapper, instantiate an explicit `OpenAI` client with a configurable timeout, return/raise errors instead of calling `exit()`, make rate-limit display provider-aware, and add unit tests with a mocked client.
