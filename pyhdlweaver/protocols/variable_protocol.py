from dataclasses import dataclass

from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols.protocol import Protocol


@dataclass(frozen=True, kw_only=True)
class VariableProtocol(Protocol):
    """Delimiter/scanner-based protocol family, intentionally out of generator scope."""

    @property
    def protocol_kind(self) -> str:
        return "variable"

    @property
    def fields(self) -> tuple[Field, ...]:
        return ()
