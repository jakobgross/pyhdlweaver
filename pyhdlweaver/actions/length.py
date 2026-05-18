from dataclasses import dataclass

from pyhdlweaver.actions.action import Action


@dataclass(frozen=True, kw_only=True)
class LengthAction(Action):
    """Base class for actions that give payload or message sizing semantics."""

    @property
    def action_kind(self) -> str:
        return "length"


@dataclass(frozen=True, kw_only=True)
class UseAsPayloadLength(LengthAction):
    """Use this field value as payload length."""

    unit_bytes: int = 1

    def __post_init__(self) -> None:
        if self.unit_bytes <= 0:
            raise ValueError("unit_bytes must be positive")


@dataclass(frozen=True, kw_only=True)
class UseAsMessageCount(LengthAction):
    """Use this field value as a count of following messages."""

    pass
