from dataclasses import dataclass

from pyhdlweaver.data_packet import DataPacket
from pyhdlweaver.protocols.fixed_protocol import FixedProtocol


@dataclass(frozen=True, kw_only=True)
class SidebandProtocol(FixedProtocol):
    """Fixed parse region whose payload ends according to stream sideband signals."""

    @property
    def protocol_kind(self) -> str:
        return "sideband"

    @property
    def is_fixed_length(self) -> bool:
        return False

    def eval(self, packet: DataPacket) -> dict[str, int | bytes]:
        values = super().eval(packet)
        values["data"] = packet.read_from(self.parse_length)
        return values

    def __post_init__(self) -> None:
        super().__post_init__()
