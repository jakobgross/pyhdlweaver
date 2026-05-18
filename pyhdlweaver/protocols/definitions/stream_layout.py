


from pyhdlweaver.protocols.definitions.bus_layout import BusLayout
from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.stream.axi_stream import AxisStream


class StreamLayout:
    """Combines an AxisStream and a BusLayout. Single entry point for parser code generation."""

    def __init__(self, stream: AxisStream, byte_offset: int = 0):
        self.stream = stream
        self.layout = BusLayout(bus_width_bits=stream.data_width, byte_offset=byte_offset)

    def field_beats(self, f: Field) -> list:
        return self.layout.field_beats(f)

    def header_beats(self, fields: list) -> int:
        return self.layout.header_beats(fields)

    def first_payload_beat(self, header_size_bytes: int) -> int:
        return self.layout.first_payload_beat(header_size_bytes)

    def last_header_beat_keep(self, header_size_bytes: int) -> int:
        """tkeep for the last header beat. Useful when the header does not end on a beat boundary."""
        last_header_byte = header_size_bytes - 1
        pos = self.layout.byte_in_beat(last_header_byte)
        return self.stream.keep_for_n_bytes(pos + 1)

    def header_ends_on_beat_boundary(self, header_size_bytes: int) -> bool:
        last_byte = self.layout.byte_offset + header_size_bytes - 1
        return (last_byte + 1) % self.stream.keep_width == 0

    def report(self, fields: list) -> str:
        lines = [
            self.stream.report(),
            "",
            self.layout.report(fields),
            "",
            f"  Header ends on beat boundary: {self.header_ends_on_beat_boundary(max(f.end_offset for f in fields))}",
        ]
        return "\n".join(lines)