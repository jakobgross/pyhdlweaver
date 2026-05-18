from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Optional, Sequence

from pyhdlweaver.data_packet import DataPacket
from pyhdlweaver.protocols.definitions.field import Field


def _fields_tuple(fields: Sequence[Field]) -> tuple[Field, ...]:
    return tuple(fields)


def _required_length(fields: Sequence[Field]) -> int:
    return max((f.end_offset for f in fields), default=0)


@dataclass(frozen=True, kw_only=True)
class Protocol(ABC):
    """Base class for protocol descriptions consumed by parser generators."""

    name: str
    next_protocol: Optional["Protocol"] = None

    @property
    @abstractmethod
    def protocol_kind(self) -> str:
        """Stable protocol family name used by sources and generators."""

    @property
    def parse_length(self) -> int:
        return _required_length(getattr(self, "fields", ()))

    @property
    def is_fixed_length(self) -> bool:
        return False

    def with_payload(self, next_protocol: "Protocol") -> "Protocol":
        """Return a copy of this protocol with a downstream payload parser attached."""

        return replace(self, next_protocol=next_protocol)

    def layers(self) -> tuple["Protocol", ...]:
        """Return this protocol and all downstream payload protocols in order."""

        layer = self
        layers: list[Protocol] = []
        while layer is not None:
            layers.append(layer)
            layer = layer.next_protocol
        return tuple(layers)

    def eval(self, packet: DataPacket) -> dict[str, int | bytes]:
        """Parse this protocol's fixed fields from packet bytes."""

        return {
            field.name: packet.read_field(field)
            for field in getattr(self, "fields", ())
        }
