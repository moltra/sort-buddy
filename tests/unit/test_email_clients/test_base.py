"""Unit tests for the abstract EmailProvider base class."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from email_clients.base import EmailProvider


def test_email_provider_is_abstract() -> None:
    with pytest.raises(TypeError):
        EmailProvider()


def test_add_flag_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        EmailProvider.add_flag(MagicMock(), 1, "SortBuddy")


def test_has_flag_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        EmailProvider.has_flag(MagicMock(), 1, "SortBuddy")
