from dataclasses import dataclass

from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols.fixed_protocol import FixedProtocol


@dataclass(frozen=True, kw_only=True)
class LengthPrefixedProtocol(FixedProtocol):
    """Fixed parse region contains a field that gives the following payload length."""

    length_field: Field

    @property
    def protocol_kind(self) -> str:
        return "length_prefixed"

    @property
    def is_fixed_length(self) -> bool:
        return False

    def __post_init__(self) -> None:
        super().__post_init__()

        if self.length_field not in self.fields:
            raise ValueError(f"{self.name}: length_field must be part of fields")
