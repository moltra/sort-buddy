"""Yahoo Mail IMAP provider."""

from __future__ import annotations

from config import EmailConfig
from email_clients.generic_imap import GenericIMAPProvider


class YahooProvider(GenericIMAPProvider):
    """Yahoo Mail IMAP provider using app-specific passwords."""

    def configure(self, config: EmailConfig) -> None:
        if not config.yahoo_username or not config.yahoo_app_password:
            raise ValueError("Yahoo username and app password are required")
        super().configure(config)
        self.host = "imap.mail.yahoo.com"
        self.port = 993
        self.use_ssl = True
        self.username = config.yahoo_username
        self.password = config.yahoo_app_password
        self.folder_prefix = config.yahoo_folder_prefix or config.folder_prefix
