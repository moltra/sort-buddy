"""Configuration management for sort-buddy."""

from __future__ import annotations

from typing import Any

from accounts_config import AccountConfig
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM provider configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
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

    _REDACT_FIELDS: frozenset[str] = frozenset({"llm_api_key"})

    def __init__(self, **values: Any) -> None:
        """Initialize with explicit keyword values taking priority over env."""
        super().__init__(**values)
        for key, value in values.items():
            if key in type(self).model_fields:
                object.__setattr__(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        data = self.model_dump()
        for field in self._REDACT_FIELDS:
            if field in data and data[field] is not None:
                data[field] = "***"
        field_repr = ", ".join(f"{k}={v!r}" for k, v in data.items())
        return f"{self.__class__.__name__}({field_repr})"


class EmailConfig(BaseSettings):
    """Email provider configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
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

    @classmethod
    def from_account_config(cls, account: AccountConfig) -> "EmailConfig":
        """Create an EmailConfig from an AccountConfig."""
        resolved = account.resolve_env_vars()
        data: dict[str, Any] = {
            "email_provider": resolved.provider,
        }

        if resolved.imap_port is not None:
            data["imap_port"] = resolved.imap_port
        if resolved.imap_use_ssl is not None:
            data["imap_use_ssl"] = resolved.imap_use_ssl
        if resolved.folder_prefix is not None:
            data["folder_prefix"] = resolved.folder_prefix

        if resolved.provider == "generic":
            data.update(
                imap_host=resolved.imap_host,
                email_username=resolved.username,
                email_password=resolved.password,
            )
        elif resolved.provider == "gmail":
            data.update(
                gmail_username=resolved.username,
                gmail_app_password=resolved.app_password,
                gmail_label_prefix=resolved.folder_prefix,
            )
        elif resolved.provider == "yahoo":
            data.update(
                yahoo_username=resolved.username,
                yahoo_app_password=resolved.app_password,
                yahoo_folder_prefix=resolved.folder_prefix,
            )

        return cls(**data)

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

    _REDACT_FIELDS: frozenset[str] = frozenset(
        {
            "email_password",
            "gmail_app_password",
            "yahoo_app_password",
        }
    )

    def __init__(self, **values: Any) -> None:
        """Initialize with explicit keyword values taking priority over env."""
        super().__init__(**values)
        for key, value in values.items():
            if key in type(self).model_fields:
                object.__setattr__(self, key, value)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        data = self.model_dump()
        for field in self._REDACT_FIELDS:
            if field in data and data[field] is not None:
                data[field] = "***"
        field_repr = ", ".join(f"{k}={v!r}" for k, v in data.items())
        return f"{self.__class__.__name__}({field_repr})"
