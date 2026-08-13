"""Unit tests for src/accounts_config.py."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from accounts_config import AccountConfig, AccountsConfig


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "accounts"


def test_from_yaml_single_valid_account() -> None:
    config = AccountsConfig.from_yaml(FIXTURES_DIR / "valid_single.yaml")
    assert len(config.accounts) == 1
    assert config.accounts[0].name == "work"
    assert config.accounts[0].provider == "generic"
    assert config.accounts[0].enabled is True
    assert config.accounts[0].folder_prefix == "AI-"


def test_from_yaml_multiple_accounts() -> None:
    config = AccountsConfig.from_yaml(FIXTURES_DIR / "valid_multiple.yaml")
    assert len(config.accounts) == 3
    names = {a.name for a in config.accounts}
    assert names == {"personal-gmail", "work", "personal-yahoo"}


def test_get_enabled_accounts_filters_disabled() -> None:
    config = AccountsConfig.from_yaml(FIXTURES_DIR / "valid_multiple.yaml")
    enabled = config.get_enabled_accounts()
    assert len(enabled) == 2
    assert {a.name for a in enabled} == {"personal-gmail", "work"}


def test_get_account_returns_enabled_account() -> None:
    config = AccountsConfig.from_yaml(FIXTURES_DIR / "valid_multiple.yaml")
    assert config.get_account("work") is not None
    assert config.get_account("work").name == "work"


def test_get_account_returns_none_for_disabled() -> None:
    config = AccountsConfig.from_yaml(FIXTURES_DIR / "valid_multiple.yaml")
    assert config.get_account("personal-yahoo") is None


def test_get_account_returns_none_for_missing() -> None:
    config = AccountsConfig.from_yaml(FIXTURES_DIR / "valid_multiple.yaml")
    assert config.get_account("missing") is None


def test_invalid_provider_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        AccountsConfig.from_yaml(FIXTURES_DIR / "invalid_provider.yaml")


def test_missing_file_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        AccountsConfig.from_yaml(FIXTURES_DIR / "does_not_exist.yaml")


def test_invalid_yaml_raises_value_error() -> None:
    with pytest.raises(ValueError):
        AccountsConfig.from_yaml(FIXTURES_DIR / "invalid_yaml.yaml")


def test_resolve_env_vars_substitutes_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORK_PASSWORD", "resolved-secret")
    account = AccountConfig(
        name="work",
        provider="generic",
        imap_host="imap.example.com",
        username="user@example.com",
        password="${WORK_PASSWORD}",
    )
    resolved = account.resolve_env_vars()
    assert resolved.password == "resolved-secret"


def test_resolve_env_vars_falls_back_to_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_VAR", raising=False)
    account = AccountConfig(
        name="work",
        provider="generic",
        imap_host="imap.example.com",
        username="user@example.com",
        password="${MISSING_VAR}",
    )
    resolved = account.resolve_env_vars()
    assert resolved.password == "${MISSING_VAR}"


def test_account_defaults() -> None:
    account = AccountConfig(
        name="minimal",
        provider="generic",
        imap_host="imap.example.com",
        username="user@example.com",
        password="secret",
    )
    assert account.enabled is True
    assert account.imap_port == 993
    assert account.imap_use_ssl is True


def test_port_and_ssl_coercion() -> None:
    account = AccountConfig(
        name="coerced",
        provider="generic",
        imap_host="imap.example.com",
        imap_port="143",
        imap_use_ssl="false",
        username="user@example.com",
        password="secret",
    )
    assert account.imap_port == 143
    assert account.imap_use_ssl is False
