from dataclasses import dataclass

from pyhdlweaver.protocols.definitions.beat_layout import BeatLayout
from pyhdlweaver.protocols.definitions.field import Field

@dataclass
class BusLayout:
    """Beat-accurate field layout for a given bus data width."""

    bus_width_bits: int
    byte_offset:    int = 0  # byte offset of this protocol layer from start of frame

    @property
    def bus_width_bytes(self) -> int:
        return self.bus_width_bits // 8

    def beat_of(self, byte: int) -> int:
        return (self.byte_offset + byte) // self.bus_width_bytes

    def byte_in_beat(self, byte: int) -> int:
        return (self.byte_offset + byte) % self.bus_width_bytes

    def field_beats(self, f: Field) -> list[BeatLayout]:
        """Return one BeatLayout per beat that contains bytes of field f (big-endian)."""
        layouts = []
        remaining_bits = f.width

        for abs_byte in range(f.offset, f.offset + f.width_bytes):
            beat        = self.beat_of(abs_byte)
            pos_in_beat = self.byte_in_beat(abs_byte)

            if layouts and layouts[-1].beat == beat:
                prev = layouts[-1]
                layouts[-1] = BeatLayout(
                    beat        = beat,
                    byte_lo     = prev.byte_lo,
                    byte_hi     = pos_in_beat,
                    field_shift = prev.field_shift,
                    mask        = prev.mask | (0xFF << (prev.field_shift - 8)),
                    is_first    = prev.is_first,
                    is_last     = False,
                )
                remaining_bits -= 8
            else:
                bits_this_frag = min(8, remaining_bits)
                layouts.append(BeatLayout(
                    beat        = beat,
                    byte_lo     = pos_in_beat,
                    byte_hi     = pos_in_beat,
                    field_shift = remaining_bits - 8,
                    mask        = (1 << bits_this_frag) - 1,
                    is_first    = len(layouts) == 0,
                    is_last     = False,
                ))
                remaining_bits -= bits_this_frag

        if layouts:
            last = layouts[-1]
            layouts[-1] = BeatLayout(
                beat        = last.beat,
                byte_lo     = last.byte_lo,
                byte_hi     = last.byte_hi,
                field_shift = last.field_shift,
                mask        = last.mask,
                is_first    = last.is_first,
                is_last     = True,
            )

        return layouts

    def header_beats(self, fields: list[Field]) -> int:
        last_byte = max(f.end_offset for f in fields) - 1
        return self.beat_of(last_byte) + 1

    def first_payload_beat(self, header_size_bytes: int) -> int:
        last_header_byte = self.byte_offset + header_size_bytes - 1
        last_header_beat = last_header_byte // self.bus_width_bytes
        return last_header_beat + 1

    def bit_slice(self, beat_layout: BeatLayout) -> tuple[int, int]:
        """
        Return (bit_hi, bit_lo) of this field fragment within tdata.
        Big-endian: byte 0 of beat is the MSB of tdata.
        """
        bit_hi = self.bus_width_bits - (beat_layout.byte_lo * 8) - 1
        bit_lo = self.bus_width_bits - (beat_layout.byte_hi * 8) - 8
        return bit_hi, bit_lo

    def report(self, fields: list[Field]) -> str:
        lines = [
            f"Bus width   : {self.bus_width_bits} bits ({self.bus_width_bytes} bytes/beat)",
            f"Layer offset: {self.byte_offset} bytes",
            "",
            f"{'Field':<20} {'Offset':>6}  {'Width':>5}  HDL slice (tdata[hi:lo])",
            "-" * 70,
        ]
        for f in fields:
            beats = self.field_beats(f)
            beat_strs = []
            for b in beats:
                hi, lo = self.bit_slice(b)
                beat_strs.append(f"beat{b.beat}[{hi}:{lo}]")
            lines.append(
                f"{f.name:<20} {f.offset:>5}B  {f.width:>4}b  " + ",  ".join(beat_strs)
            )
        return "\n".join(lines)