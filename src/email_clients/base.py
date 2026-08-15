"""Abstract base class for email providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from config import EmailConfig


class EmailProvider(ABC):
    """Abstract interface for email providers."""

    unseen_ids: list[int]
    current_index: int

    @abstractmethod
    def configure(self, config: EmailConfig) -> None:
        """Configure the provider from an EmailConfig."""
        ...

    @abstractmethod
    def connect(self, dry_run: bool = False) -> None:
        """Connect to the email server."""
        ...

    @abstractmethod
    def list_ai_folders(self) -> list[str]:
        """Return folders matching the configured prefix."""
        ...

    @abstractmethod
    def fetch_next_message(self) -> dict[str, Any] | None:
        """Fetch and parse the next unseen message."""
        ...

    @abstractmethod
    def move_message(self, message_id: int | str, target_folder: str) -> bool:
        """Move a message to the target folder."""
        ...

    @abstractmethod
    def has_more_messages(self) -> bool:
        """Return True if there are more unseen messages to process."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the connection."""
        ...

    @abstractmethod
    def add_flag(self, message_id: int | str, flag: str) -> None:
        """Add a keyword flag to a message."""
        raise NotImplementedError

    @abstractmethod
    def has_flag(self, message_id: int | str, flag: str) -> bool:
        """Return True if a message has the given keyword flag."""
        raise NotImplementedError

    @abstractmethod
    def create_folder(self, folder_name: str) -> bool:
        """Create a folder on the email server."""
        ...
