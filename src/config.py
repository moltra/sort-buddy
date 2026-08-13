"""Configuration management for sort-buddy."""

from __future__ import annotations

import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM provider configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "openai"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout: float | None = None

    @model_validator(mode="after")
    def map_legacy_openai(self) -> "LLMConfig":
        """Map legacy OPENAI_* env vars to LLM_* fields when provider is openai."""
        if not self.llm_provider or self.llm_provider == "openai":
            if not self.llm_api_key:
                self.llm_api_key = os.environ.get("OPENAI_API_KEY")
            if not self.llm_base_url:
                self.llm_base_url = os.environ.get("OPENAI_API_URL")
            if not self.llm_model:
                self.llm_model = os.environ.get("OPENAI_MODEL")
        return self
