"""Factory for creating email provider instances."""

from __future__ import annotations

from config import EmailConfig
from email_clients.base import EmailProvider
from email_clients.generic_imap import GenericIMAPProvider
from email_clients.gmail_provider import GmailProvider
from email_clients.yahoo_provider import YahooProvider


def create_email_provider(
    config: EmailConfig,
    dry_run: bool = False,
    imap_client_class: type | None = None,
) -> EmailProvider:
    """Create, configure, and connect an email provider for the given config."""
    if config.email_provider == "generic":
        provider: EmailProvider = GenericIMAPProvider(
            imap_client_class=imap_client_class
        )
    elif config.email_provider == "gmail":
        provider = GmailProvider(imap_client_class=imap_client_class)
    elif config.email_provider == "yahoo":
        provider = YahooProvider(imap_client_class=imap_client_class)
    else:
        raise ValueError(f"Unknown email provider: {config.email_provider}")

    provider.configure(config)
    provider.connect(dry_run=dry_run)
    return provider
