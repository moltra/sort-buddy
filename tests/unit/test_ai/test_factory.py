"""Unit tests for the AI client factory."""

import pytest

from ai.factory import create_ai_client
from ai.openai_client import OpenAIClient
from ai.ollama_client import OllamaClient
from config import LLMConfig


def test_factory_creates_openai_client():
    config = LLMConfig(
        llm_provider="openai",
        llm_base_url="https://api.openai.com/v1/",
        llm_api_key="key",
        llm_model="gpt-4",
    )
    client = create_ai_client(config)
    assert isinstance(client, OpenAIClient)


def test_factory_creates_ollama_client():
    config = LLMConfig(
        llm_provider="ollama",
        llm_base_url="http://localhost:11434/v1/",
        llm_api_key="",
        llm_model="llama3.1",
    )
    client = create_ai_client(config)
    assert isinstance(client, OllamaClient)


def test_factory_rejects_unknown_provider():
    config = LLMConfig(
        llm_provider="unknown",
        llm_base_url="https://example.com/v1/",
        llm_api_key="key",
        llm_model="model",
    )
    with pytest.raises(ValueError, match="Unknown AI provider"):
        create_ai_client(config)
