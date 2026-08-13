"""Generic IMAP email provider."""

from __future__ import annotations

import socket
import time
from typing import Any

import imapclient
from imapclient.exceptions import IMAPClientError, LoginError
from loguru import logger

from config import EmailConfig
from email_clients.base import EmailProvider
from email_clients.parsers import build_message_dict


class GenericIMAPProvider(EmailProvider):
    """Generic IMAP provider with retry/backoff and timeout handling."""

    def __init__(self, imap_client_class: type | None = None) -> None:
        self._imap_client_class = imap_client_class or imapclient.IMAPClient
        self.config: EmailConfig | None = None
        self.client: Any = None
        self.unseen_ids: list[int] = []
        self.current_index: int = 0
        self.dry_run: bool = False
        self.host: str = ""
        self.port: int = 993
        self.use_ssl: bool = True
        self.username: str = ""
        self.password: str = ""
        self.folder_prefix: str = "AI-"
        self._flag_name: str = "SortBuddy"

    def configure(self, config: EmailConfig) -> None:
        """Configure the provider from an EmailConfig."""
        self.config = config
        self.host = config.imap_host or ""
        self.port = config.imap_port
        self.use_ssl = config.imap_use_ssl
        self.username = config.email_username or ""
        self.password = config.email_password or ""
        self.folder_prefix = config.folder_prefix

    def _validate_config(self) -> None:
        if not self.host or not self.username or not self.password:
            raise ValueError("IMAP host, username, and password are required")

    def _search_unseen_without_flag(self, flag: str) -> list[int]:
        return self.client.search(["UNSEEN", "NOT", "KEYWORD", flag])

    def connect(self, dry_run: bool = False) -> None:
        """Connect to the IMAP server with retry and backoff."""
        self.dry_run = dry_run
        self._validate_config()
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                self.client = self._imap_client_class(
                    self.host, port=self.port, ssl=self.use_ssl
                )
                self.client.login(self.username, self.password)
                self.client.select_folder("INBOX", readonly=False)
                self.unseen_ids = self._search_unseen_without_flag(self._flag_name)
                self.current_index = 0
                return
            except (IMAPClientError, LoginError, socket.error) as exc:
                last_error = exc
                logger.exception("IMAP connect failed on attempt %d", attempt + 1)
                if attempt < 2:
                    time.sleep(2**attempt)
        raise ConnectionError(
            f"Failed to connect to IMAP after 3 attempts: {last_error}"
        ) from last_error

    def list_ai_folders(self) -> list[str]:
        """Return folders matching the configured prefix."""
        folders = self.client.list_folders()
        return [folder[2] for folder in folders if folder[2].startswith(self.folder_prefix)]

    def fetch_next_message(self) -> dict[str, Any] | None:
        """Fetch and parse the next unseen message."""
        if self.current_index >= len(self.unseen_ids):
            return None

        msg_id = self.unseen_ids[self.current_index]
        self.current_index += 1

        message_data = self.client.fetch(
            msg_id, ["ENVELOPE", "BODY[TEXT]", "RFC822"]
        )[msg_id]
        envelope = message_data[b"ENVELOPE"]
        rfc822 = message_data[b"RFC822"]

        self._set_unseen(msg_id)
        if not self.dry_run:
            self._add_flag(msg_id, self._flag_name)

        return build_message_dict(msg_id, envelope, rfc822)

    def _set_unseen(self, msg_id: int) -> None:
        self.client.remove_flags(msg_id, [b"\\Seen"])

    def _add_flag(self, msg_id: int, flag: str) -> None:
        self.client.add_flags(msg_id, [flag])

    def add_flag(self, message_id: int | str, flag: str) -> None:
        """Add a keyword flag to a message, respecting dry-run mode."""
        if not self.dry_run:
            self._add_flag(int(message_id), flag)

    def has_flag(self, message_id: int | str, flag: str) -> bool:
        """Return True if a message has the given keyword flag."""
        msg_id = int(message_id)
        flags = self.client.get_flags(msg_id)
        msg_flags = flags[msg_id]
        return flag.encode("utf-8") in msg_flags

    def has_more_messages(self) -> bool:
        """Return True if there are more unseen messages to process."""
        return self.current_index < len(self.unseen_ids)

    def move_message(self, message_id: int | str, target_folder: str) -> bool:
        """Move a message to the target folder."""
        if self.dry_run:
            return True
        mid = int(message_id)
        self.client.copy(mid, target_folder)
        self.client.delete_messages([mid])
        self.client.expunge()
        return True

    def close(self) -> None:
        """Close the IMAP connection."""
        if self.client is not None:
            self.client.logout()
