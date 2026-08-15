"""Compatibility wrapper around the new email service layer."""

from __future__ import annotations

import socket
from typing import Any

import imapclient  # type: ignore[import-untyped]
from imapclient.exceptions import IMAPClientError, LoginError  # type: ignore[import-untyped]
from loguru import logger

from config import EmailConfig
from email_clients.factory import create_email_provider

IMAPClient = imapclient.IMAPClient


class EmailFetcher:
    """Thin compatibility wrapper that delegates to the new email providers."""

    def __init__(
        self,
        dry_run: bool = False,
        email_config: EmailConfig | None = None,
    ) -> None:
        self.dry_run = dry_run
        config = email_config if email_config is not None else EmailConfig()
        self._provider = create_email_provider(
            config,
            dry_run=dry_run,
            imap_client_class=IMAPClient,
        )

    @property
    def unseen_ids(self) -> list[int]:
        """List of unseen message ids waiting to be processed."""
        return self._provider.unseen_ids

    @property
    def current_index(self) -> int:
        """Index of the next message to fetch."""
        return self._provider.current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        self._provider.current_index = value

    def list_ai_folders(self) -> list[str]:
        return self._provider.list_ai_folders()

    def fetch_next_message(self) -> dict[str, Any] | None:
        return self._provider.fetch_next_message()

    def add_flag(self, message_id: int | str, flag: str) -> None:
        self._provider.add_flag(message_id, flag)

    def has_flag(self, message_id: int | str, flag: str) -> bool:
        return self._provider.has_flag(message_id, flag)

    def has_more_messages(self) -> bool:
        return self._provider.has_more_messages()

    def move_message(self, message_id: int | str, target_folder: str) -> None:
        try:
            self._provider.move_message(message_id, target_folder)
        except (IMAPClientError, LoginError, socket.error) as exc:
            logger.exception("Failed to move message %s to %s", message_id, target_folder)
            raise

    def connect(self) -> None:
        self._provider.connect(dry_run=self.dry_run)

    def create_folder(self, folder_name: str) -> bool:
        return self._provider.create_folder(folder_name)

    def close(self) -> None:
        self._provider.close()
