"""Gmail IMAP provider."""

from __future__ import annotations

from config import EmailConfig
from email_clients.generic_imap import GenericIMAPProvider


class GmailProvider(GenericIMAPProvider):
    """Gmail IMAP provider using app-specific passwords."""

    def configure(self, config: EmailConfig) -> None:
        if not config.gmail_username or not config.gmail_app_password:
            raise ValueError("Gmail username and app password are required")
        super().configure(config)
        self.host = "imap.gmail.com"
        self.port = 993
        self.use_ssl = True
        self.username = config.gmail_username
        self.password = config.gmail_app_password
        self.folder_prefix = config.gmail_label_prefix or config.folder_prefix
