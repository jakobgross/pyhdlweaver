from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Action(ABC):
    """Base class for field actions used by parser generators."""

    @property
    @abstractmethod
    def action_kind(self) -> str:
        """Stable action family name used by sources and generators."""
