"""Generate SystemVerilog for the all-in-one HFT parser."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.all_in_one_hft.all_in_one_hft import ALL_IN_ONE_HFT_PARSER
from pyhdlweaver.generators import SystemVerilogGenerator
from pyhdlweaver.stream.axi_stream import STREAM_8, STREAM_64

HDL_DIR = Path(__file__).resolve().parent / "hdl"


def generate_8bit():
    return SystemVerilogGenerator().generate(
        ALL_IN_ONE_HFT_PARSER, STREAM_8, module_name="all_in_one_hft_parser_8bit"
    )


def generate_64bit():
    return SystemVerilogGenerator().generate(
        ALL_IN_ONE_HFT_PARSER, STREAM_64, module_name="all_in_one_hft_parser_64bit"
    )


def main():
    HDL_DIR.mkdir(parents=True, exist_ok=True)
    for fn in (generate_8bit, generate_64bit):
        g = fn()
        out = HDL_DIR / g.name
        out.write_text(g.content)
        print(out)


if __name__ == "__main__":
    main()
