from dataclasses import dataclass

from pyhdlweaver.actions.action import Action


@dataclass(frozen=True, kw_only=True)
class CaptureAction(Action):
    """Base class for actions that expose field values outside the parser."""

    @property
    def action_kind(self) -> str:
        return "capture"


@dataclass(frozen=True, kw_only=True)
class CaptureToMetadata(CaptureAction):
    """Pass the field value downstream as parser metadata."""

    name: str | None = None

    def metadata_name(self, field_name: str) -> str:
        return self.name or field_name

    def __post_init__(self) -> None:
        if self.name == "":
            raise ValueError("metadata name must be non-empty")


@dataclass(frozen=True, kw_only=True)
class CaptureToRegister(CaptureAction):
    """Store the field value in a readable status register."""

    register: str | None = None

    def register_name(self, field_name: str) -> str:
        return self.register or field_name

    def __post_init__(self) -> None:
        if self.register == "":
            raise ValueError("register name must be non-empty")
