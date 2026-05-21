from dataclasses import dataclass

from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols.discriminated_protocol import DiscriminatedProtocol


@dataclass(frozen=True, kw_only=True)
class LengthPrefixedDiscriminatedSubProtocol:
    """Length-prefixed sub-message whose payload is parsed by a DiscriminatedProtocol."""

    name: str
    length_field: Field
    discriminated: DiscriminatedProtocol

    @property
    def total_length(self) -> int:
        return self.length_field.offset + self.length_field.width_bytes

    @property
    def parse_length(self) -> int:
        return self.total_length

    @property
    def fields(self) -> tuple[Field, ...]:
        return (self.length_field,)
