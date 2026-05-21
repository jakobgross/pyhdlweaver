from dataclasses import dataclass


@dataclass(frozen=True)
class AxisStream:
    """AXI-Stream bus definition parameterised on data width."""

    data_width: int
    user_width: int = 1
    tdest_width: int = 4

    def __post_init__(self):
        if self.data_width % 8 != 0:
            raise ValueError(f"data_width must be a multiple of 8, got {self.data_width}")
        if self.data_width < 8:
            raise ValueError(f"data_width must be >= 8, got {self.data_width}")

    @property
    def keep_width(self) -> int:
        return self.data_width // 8

    @property
    def keep_all(self) -> int:
        return (1 << self.keep_width) - 1

    def keep_for_n_bytes(self, n: int) -> int:
        """tkeep value for n valid bytes at the start of the beat (big-endian, MSB first)."""
        if not 1 <= n <= self.keep_width:
            raise ValueError(f"n={n} out of range [1, {self.keep_width}]")
        return ((1 << n) - 1) << (self.keep_width - n)

    def n_valid_bytes(self, tkeep: int) -> int:
        return bin(tkeep).count('1')

    @property
    def signals(self) -> dict:
        """Signal name to width in bits. tvalid and tready are flow control, not included."""
        return {
            "tdata": self.data_width,
            "tkeep": self.keep_width,
            "tlast": 1,
            "tuser": self.user_width,
        }

    def report(self) -> str:
        lines = [
            f"AXI-Stream  data_width={self.data_width}b  keep_width={self.keep_width}b  user_width={self.user_width}b",
            f"  tdata  [{self.data_width-1}:0]",
            f"  tkeep  [{self.keep_width-1}:0]  (keep_all = 0b{self.keep_all:0{self.keep_width}b})",
            "  tlast  [0]",
            f"  tuser  [{self.user_width-1}:0]  (bit 0 = frame error)",
            "  tvalid [0]  (flow control)",
            "  tready [0]  (flow control)",
        ]
        return "\n".join(lines)


STREAM_8  = AxisStream(data_width=8)
STREAM_32 = AxisStream(data_width=32)
STREAM_64 = AxisStream(data_width=64)
STREAM_80 = AxisStream(data_width=80)
