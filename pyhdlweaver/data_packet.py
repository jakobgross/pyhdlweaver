from dataclasses import dataclass

from pyhdlweaver.protocols.definitions.field import Field


@dataclass(frozen=True)
class DataPacket:
    """Byte-backed packet used as a software golden model for parser tests."""

    data: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.data, bytes):
            raise TypeError("DataPacket data must be bytes")

    def read_field(self, field: Field) -> int:
        if field.end_offset > len(self.data):
            raise ValueError(
                f"field {field.name!r} ends at byte {field.end_offset}, "
                f"but packet has {len(self.data)} bytes"
            )

        value = int.from_bytes(
            self.data[field.offset:field.end_offset],
            byteorder="big",
        )
        extra_bits = field.width_bytes * 8 - field.width
        if extra_bits:
            value &= (1 << field.width) - 1
        return value

    def read_from(self, offset: int) -> bytes:
        if offset > len(self.data):
            raise ValueError(
                f"offset {offset} is past the end of packet with {len(self.data)} bytes"
            )
        return self.data[offset:]
