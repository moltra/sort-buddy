"""Compatibility wrapper around the new AI service layer."""

from __future__ import annotations

from ai.base import AIClient
from ai.factory import create_ai_client
from ai.prompts import generate_prompt as _generate_prompt
from config import LLMConfig

__all__ = [
    "configure_openai",
    "generate_prompt",
    "get_ai_response",
    "get_ai_response_from_message",
]

_client: AIClient | None = None


def configure_openai() -> None:
    """Configure the global AI client from environment variables."""
    global _client
    config = LLMConfig()
    _client = create_ai_client(config)


def generate_prompt(message: dict[str, str], folders: list[str], show_prompt: bool = False) -> tuple[str, str]:
    """Generate a system and user prompt for an email message."""
    return _generate_prompt(message, folders, show_prompt)


def get_ai_response(prompt: str, system_prompt: str, folders: list[str], show_rate_limits: bool = False) -> tuple[str, str]:
    """Get an AI classification from a pre-built prompt pair."""
    if _client is None:
        configure_openai()
    # Use a synthetic message so the shared client can be reused. The
    # supplied user prompt is placed in the message body.
    message = {
        "subject": "",
        "from": "",
        "body": prompt,
    }
    return _client.classify_email(
        message,
        folders,
        show_prompt=False,
        show_rate_limits=show_rate_limits,
        system_prompt=system_prompt,
    )


def get_ai_response_from_message(
    message: dict[str, str],
    folders: list[str],
    show_prompt: bool = False,
    show_rate_limits: bool = False,
) -> tuple[str, str]:
    """Get an AI classification for an email message dictionary."""
    if _client is None:
        configure_openai()
    return _client.classify_email(message, folders, show_prompt, show_rate_limits)
