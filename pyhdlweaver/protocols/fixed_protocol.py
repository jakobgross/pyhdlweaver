from dataclasses import dataclass, field
from typing import Optional, Sequence

from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols.protocol import (
    Protocol,
    _fields_tuple,
    _required_length,
)


@dataclass(frozen=True, kw_only=True)
class FixedProtocol(Protocol):
    """All fields and the complete protocol length are known at elaboration time."""

    fields: Sequence[Field] = field(default_factory=tuple)
    total_length: Optional[int] = None

    @property
    def protocol_kind(self) -> str:
        return "fixed"

    @property
    def is_fixed_length(self) -> bool:
        return self.total_length is not None

    @property
    def parse_length(self) -> int:
        if self.total_length is None:
            return _required_length(self.fields)
        return self.total_length

    def __post_init__(self) -> None:
        fields = _fields_tuple(self.fields)
        object.__setattr__(self, "fields", fields)

        required_length = _required_length(fields)
        if self.total_length is None:
            object.__setattr__(self, "total_length", required_length)
        elif self.total_length < required_length:
            raise ValueError(
                f"{self.name}: total_length={self.total_length} does not cover "
                f"fields ending at byte {required_length}"
            )
