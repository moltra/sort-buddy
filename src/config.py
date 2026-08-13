"""Configuration management for sort-buddy."""

from __future__ import annotations

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM provider configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "openai"
    llm_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_BASE_URL", "OPENAI_API_URL"),
    )
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"),
    )
    llm_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_MODEL", "OPENAI_MODEL"),
    )
    llm_timeout: float = Field(default=60.0, gt=0.0)

    @model_validator(mode="after")
    def _configure(self) -> "LLMConfig":
        """Apply provider defaults and validate."""
        if not self.llm_provider:
            self.llm_provider = "openai"

        if self.llm_provider == "openai":
            if self.llm_base_url is None:
                self.llm_base_url = "https://api.openai.com/v1/"
            if self.llm_api_key is None or self.llm_model is None:
                raise ValueError(
                    "OpenAI provider requires llm_api_key and llm_model"
                )

        elif self.llm_provider == "ollama":
            if self.llm_base_url is None:
                self.llm_base_url = "http://localhost:11434/v1/"
            if self.llm_api_key is None:
                self.llm_api_key = "ollama"
            if self.llm_model is None:
                raise ValueError("Ollama provider requires llm_model")

        return self


class EmailConfig(BaseSettings):
    """Email provider configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    email_provider: str = "generic"
    imap_host: str | None = Field(
        default=None,
        validation_alias=AliasChoices("IMAP_HOST"),
    )
    imap_port: int = Field(default=993, ge=1, le=65535)
    imap_use_ssl: bool = True
    email_username: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMAIL_USERNAME"),
    )
    email_password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMAIL_PASSWORD"),
    )

    gmail_username: str | None = None
    gmail_app_password: str | None = None
    gmail_label_prefix: str | None = None

    yahoo_username: str | None = None
    yahoo_app_password: str | None = None
    yahoo_folder_prefix: str | None = None

    folder_prefix: str = "AI-"

    @model_validator(mode="after")
    def _configure(self) -> "EmailConfig":
        """Validate provider-specific requirements."""
        if self.email_provider == "generic":
            if not self.imap_host or not self.email_username or not self.email_password:
                raise ValueError(
                    "Generic IMAP provider requires imap_host, email_username, and email_password"
                )

        elif self.email_provider == "gmail":
            if not self.gmail_username or not self.gmail_app_password:
                raise ValueError(
                    "Gmail username and app password are required"
                )

        elif self.email_provider == "yahoo":
            if not self.yahoo_username or not self.yahoo_app_password:
                raise ValueError(
                    "Yahoo username and app password are required"
                )

        return self
