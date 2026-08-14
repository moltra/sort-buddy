"""OpenAI API client implementation."""

from __future__ import annotations

import openai

from ai.base import AIClient
from ai.prompts import (
    generate_json_prompt,
    generate_prompt,
    parse_classification,
    parse_json_classification,
)
from config import LLMConfig

_RATE_LIMIT_HEADERS = [
    ("x-ratelimit-limit-requests", "Rate Limit Requests"),
    ("x-ratelimit-limit-tokens", "Rate Limit Tokens"),
    ("x-ratelimit-limit-tokens_usage_based", "Rate Limit Tokens Usage Based"),
    ("x-ratelimit-remaining-requests", "Rate Limit Remaining Requests"),
    ("x-ratelimit-remaining-tokens", "Rate Limit Remaining Tokens"),
    ("x-ratelimit-remaining-tokens_usage_based", "Rate Limit Remaining Tokens Usage Based"),
    ("x-ratelimit-reset-requests", "Rate Limit Reset Requests"),
    ("x-ratelimit-reset-tokens", "Rate Limit Reset Tokens"),
    ("x-ratelimit-reset-tokens_usage_based", "Rate Limit Reset Tokens Usage Based"),
]


class OpenAIClient(AIClient):
    """Client for the OpenAI chat completions API."""

    DEFAULT_TIMEOUT: float = 30.0

    def __init__(self) -> None:
        self._client: openai.OpenAI | None = None
        self._config: LLMConfig | None = None

    def configure(self, config: LLMConfig) -> None:
        """Configure the underlying OpenAI client."""
        self._config = config
        timeout = config.llm_timeout if config.llm_timeout is not None else self.DEFAULT_TIMEOUT
        self._client = openai.OpenAI(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            timeout=timeout,
        )

    def classify_email(
        self,
        message: dict[str, str],
        folders: list[str],
        show_prompt: bool = False,
        show_rate_limits: bool = False,
        system_prompt: str = "",
        use_json_mode: bool = False,
    ) -> tuple[str, str]:
        """Classify an email using the OpenAI API."""
        if self._client is None or self._config is None:
            raise RuntimeError("Client not configured")

        prompt_builder = generate_json_prompt if use_json_mode else generate_prompt
        parser = parse_json_classification if use_json_mode else parse_classification
        default_system, prompt = prompt_builder(message, folders, show_prompt)
        final_system = system_prompt if system_prompt else default_system

        chat_kwargs: dict[str, object] = {
            "model": self._config.llm_model,
            "messages": [
                {"role": "system", "content": final_system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 128,
        }
        if use_json_mode:
            chat_kwargs["response_format"] = {"type": "json_object"}

        try:
            raw = self._client.chat.completions.with_raw_response.create(**chat_kwargs)
        except (
            openai.APIError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.APITimeoutError,
        ) as exc:
            return ("invalid", f"AI request failed: {exc}")

        if show_rate_limits and raw.headers:
            for header, label in _RATE_LIMIT_HEADERS:
                print(f"{label}: {raw.headers.get(header)}")

        response = raw.parse()
        try:
            content = response.choices[0].message.content
        except (IndexError, AttributeError):
            return ("invalid", "empty or malformed AI response")
        if not content:
            return ("invalid", "empty or malformed AI response")
        return parser(content, folders)

    def health_check(self) -> bool:
        """Check the OpenAI API by listing available models."""
        if self._client is None:
            return False
        try:
            self._client.models.list()
            return True
        except (
            openai.APIError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.APITimeoutError,
        ):
            return False
