"""Email service layer for sort-buddy."""

from __future__ import annotations

from email_clients.base import EmailProvider
from email_clients.factory import create_email_provider
from email_clients.generic_imap import GenericIMAPProvider
from email_clients.gmail_provider import GmailProvider
from email_clients.yahoo_provider import YahooProvider
from email_clients.parsers import (
    build_message_dict,
    extract_text_from_email,
    format_from_address,
)

__all__ = [
    "EmailProvider",
    "GenericIMAPProvider",
    "GmailProvider",
    "YahooProvider",
    "create_email_provider",
    "build_message_dict",
    "extract_text_from_email",
    "format_from_address",
]
