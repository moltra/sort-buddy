"""Multi-account YAML configuration models."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, field_validator, ValidationError


class AccountConfig(BaseModel):
    """Configuration for a single email account."""

    name: str
    provider: str
    enabled: bool = True
    imap_host: str | None = None
    imap_port: int | None = 993
    imap_use_ssl: bool | None = True
    username: str | None = None
    password: str | None = None
    app_password: str | None = None
    folder_prefix: str | None = None

    @field_validator("provider")
    @classmethod
    def _validate_provider(cls, value: str) -> str:
        if value not in {"generic", "gmail", "yahoo"}:
            raise ValueError(f"Unknown email provider: {value}")
        return value

    @field_validator("imap_port", mode="before")
    @classmethod
    def _port_int(cls, value: Any) -> int | None:
        if value is None:
            return None
        return int(value)

    @field_validator("imap_use_ssl", mode="before")
    @classmethod
    def _use_ssl_bool(cls, value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"true", "1", "yes", "on"}

    def resolve_env_vars(self) -> "AccountConfig":
        """Return a new AccountConfig with ${VAR} placeholders replaced."""
        pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
        data = self.model_dump()

        def _replace(match: re.Match[str]) -> str:
            var = match.group(1)
            return os.environ.get(var, match.group(0))

        for key, value in data.items():
            if isinstance(value, str):
                data[key] = pattern.sub(_replace, value)

        return AccountConfig(**data)

    _REDACT_FIELDS: frozenset[str] = frozenset(
        {
            "password",
            "app_password",
            "api_key",
            "gmail_app_password",
            "yahoo_app_password",
            "email_password",
        }
    )

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        data = self.model_dump()
        for field in self._REDACT_FIELDS:
            if field in data and data[field] is not None:
                data[field] = "***"
        field_repr = ", ".join(f"{k}={v!r}" for k, v in data.items())
        return f"{self.__class__.__name__}({field_repr})"


class AccountsConfig(BaseModel):
    """Top-level container for a list of account configurations."""

    accounts: list[AccountConfig]

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AccountsConfig":
        """Load and validate accounts from a YAML file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Accounts file not found: {path}")

        try:
            raw = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in accounts file: {exc}") from exc

        if not isinstance(raw, dict) or "accounts" not in raw:
            raise ValueError("Accounts file must contain an 'accounts' list")

        return cls(**raw)

    def get_enabled_accounts(self) -> list[AccountConfig]:
        """Return all accounts marked as enabled."""
        return [a for a in self.accounts if a.enabled]

    def get_account(self, name: str) -> AccountConfig | None:
        """Return an enabled account by name."""
        for account in self.get_enabled_accounts():
            if account.name == name:
                return account
        return None
