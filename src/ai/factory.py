"""Factory for creating AI client instances."""

from __future__ import annotations

from ai.base import AIClient
from ai.openai_client import OpenAIClient
from ai.ollama_client import OllamaClient
from config import LLMConfig


def create_ai_client(config: LLMConfig) -> AIClient:
    """Create and configure an AI client for the configured provider."""
    if config.llm_provider == "openai":
        client = OpenAIClient()
    elif config.llm_provider == "ollama":
        client = OllamaClient()
    else:
        raise ValueError(f"Unknown AI provider: {config.llm_provider}")

    client.configure(config)
    return client
