"""Ollama OpenAI-compatible client implementation."""

from __future__ import annotations

import openai

from ai.base import AIClient
from ai.prompts import generate_prompt, parse_classification
from config import LLMConfig


class OllamaClient(AIClient):
    """Client for an Ollama instance exposed via its OpenAI-compatible endpoint."""

    DEFAULT_TIMEOUT: float = 60.0
    DEFAULT_API_KEY: str = "ollama"

    def __init__(self) -> None:
        self._client: openai.OpenAI | None = None
        self._config: LLMConfig | None = None

    def configure(self, config: LLMConfig) -> None:
        """Configure the underlying client for the Ollama endpoint."""
        self._config = config
        timeout = config.llm_timeout if config.llm_timeout is not None else self.DEFAULT_TIMEOUT
        api_key = config.llm_api_key if config.llm_api_key else self.DEFAULT_API_KEY
        self._client = openai.OpenAI(
            base_url=config.llm_base_url,
            api_key=api_key,
            timeout=timeout,
        )

    def classify_email(
        self,
        message: dict[str, str],
        folders: list[str],
        show_prompt: bool = False,
        show_rate_limits: bool = False,
        system_prompt: str = "",
    ) -> tuple[str, str]:
        """Classify an email using an Ollama model."""
        if self._client is None or self._config is None:
            raise RuntimeError("Client not configured")

        default_system, prompt = generate_prompt(message, folders, show_prompt)
        final_system = system_prompt if system_prompt else default_system

        try:
            raw = self._client.chat.completions.with_raw_response.create(
                model=self._config.llm_model,
                messages=[
                    {"role": "system", "content": final_system},
                    {"role": "user", "content": prompt},
                ],
            )
        except (
            openai.APIError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.APITimeoutError,
        ) as exc:
            return ("invalid", f"AI request failed: {exc}")

        # Ollama does not provide OpenAI-style rate limit headers.
        if show_rate_limits and raw.headers:
            pass

        response = raw.parse()
        try:
            content = response.choices[0].message.content
        except (IndexError, AttributeError):
            return ("invalid", "empty or malformed AI response")
        if not content:
            return ("invalid", "empty or malformed AI response")
        return parse_classification(content, folders)

    def health_check(self) -> bool:
        """Check the Ollama endpoint by listing available models."""
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
