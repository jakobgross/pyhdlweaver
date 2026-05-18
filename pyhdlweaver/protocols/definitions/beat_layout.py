from dataclasses import dataclass

@dataclass(frozen=True)
class BeatLayout:
    """Describes where a field fragment lands in a single bus beat."""

    beat:        int
    byte_lo:     int   # first byte of fragment within beat (0-based)
    byte_hi:     int   # last byte of fragment within beat (inclusive)
    field_shift: int   # bits to shift fragment to align to bit 0 of field
    mask:        int   # bitmask for this fragment
    is_first:    bool  # this beat contains the MSB of the field
    is_last:     bool  # this beat contains the LSB of the field

    @property
    def n_bytes(self) -> int:
        return self.byte_hi - self.byte_lo + 1

    @property
    def n_bits(self) -> int:
        return self.n_bytes * 8