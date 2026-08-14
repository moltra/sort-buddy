"""Ollama OpenAI-compatible client implementation."""

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
        use_json_mode: bool = False,
    ) -> tuple[str, str]:
        """Classify an email using an Ollama model."""
        if self._client is None or self._config is None:
            raise RuntimeError("Client not configured")

        prompt_builder = generate_json_prompt if use_json_mode else generate_prompt
        parser = parse_json_classification if use_json_mode else parse_classification
        default_system, prompt = prompt_builder(message, folders, show_prompt)
        final_system = system_prompt if system_prompt else default_system

        messages = [
            {"role": "system", "content": final_system},
            {"role": "user", "content": prompt},
        ]

        chat_kwargs: dict[str, object] = {
            "model": self._config.llm_model,
            "messages": messages,
        }
        if use_json_mode:
            chat_kwargs["response_format"] = {"type": "json_object"}

        try:
            raw = self._client.chat.completions.with_raw_response.create(**chat_kwargs)
        except openai.BadRequestError:
            if not use_json_mode:
                return ("invalid", "AI request rejected by the endpoint")
            try:
                del chat_kwargs["response_format"]
                chat_kwargs["extra_body"] = {"format": "json"}
                raw = self._client.chat.completions.with_raw_response.create(**chat_kwargs)
            except (
                openai.APIError,
                openai.APIConnectionError,
                openai.RateLimitError,
                openai.APITimeoutError,
            ) as exc:
                return ("invalid", f"AI request failed: {exc}")
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
        return parser(content, folders)

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
