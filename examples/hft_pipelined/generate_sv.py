"""Generate SV modules for the hft_pipelined example."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.itch.itch import ITCH_PARSER
from examples.mold_udp.mold_udp import MOLD_UDP_PARSER
from examples.udp.udp import UDP_PORT_ROUTER
from pyhdlweaver.generators import SystemVerilogGenerator
from pyhdlweaver.stream.axi_stream import STREAM_8, STREAM_64

HDL_DIR = Path(__file__).resolve().parent / "hdl"


def generate_udp_port_router_8bit():
    return SystemVerilogGenerator().generate(UDP_PORT_ROUTER, STREAM_8, module_name="udp_port_router_8bit")


def generate_mold_udp_8bit():
    return SystemVerilogGenerator().generate(MOLD_UDP_PARSER, STREAM_8, module_name="mold_udp_8bit")


def generate_itch_parser_8bit():
    return SystemVerilogGenerator().generate(ITCH_PARSER, STREAM_8, module_name="itch_parser_8bit")


def generate_udp_port_router_64bit():
    return SystemVerilogGenerator().generate(UDP_PORT_ROUTER, STREAM_64, module_name="udp_port_router_64bit")


def generate_mold_udp_64bit():
    return SystemVerilogGenerator().generate(MOLD_UDP_PARSER, STREAM_64, module_name="mold_udp_64bit")


def generate_itch_parser_64bit():
    return SystemVerilogGenerator().generate(ITCH_PARSER, STREAM_64, module_name="itch_parser_64bit")


def main():
    HDL_DIR.mkdir(parents=True, exist_ok=True)
    generators = (
        generate_udp_port_router_8bit, generate_mold_udp_8bit, generate_itch_parser_8bit,
        generate_udp_port_router_64bit, generate_mold_udp_64bit, generate_itch_parser_64bit,
    )
    for fn in generators:
        g = fn()
        out = HDL_DIR / g.name
        out.write_text(g.content)
        print(out)


if __name__ == "__main__":
    main()
