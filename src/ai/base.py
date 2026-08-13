"""Abstract AI client interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from config import LLMConfig


class AIClient(ABC):
    """Abstract base class for AI email classification clients."""

    @abstractmethod
    def configure(self, config: LLMConfig) -> None:
        """Configure the client with the provided LLM configuration."""
        ...

    @abstractmethod
    def classify_email(
        self,
        message: dict[str, str],
        folders: list[str],
        show_prompt: bool = False,
        show_rate_limits: bool = False,
        system_prompt: str = "",
    ) -> tuple[str, str]:
        """Classify an email into one of the supplied folders."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check whether the AI provider is reachable."""
        ...
