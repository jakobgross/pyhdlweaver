import sys
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.eth_ip.eth_ip import IP_FORWARD_UDP_PARSER, IP_PARSER
from pyhdlweaver.generators import GeneratedFile, SystemVerilogGenerator
from pyhdlweaver.stream.axi_stream import STREAM_8, STREAM_32

EXAMPLE_DIR = Path(__file__).resolve().parent
HDL_DIR = EXAMPLE_DIR / "hdl"
DEFAULT_OUTPUT = HDL_DIR / "eth_ip_parser.sv"
DEFAULT_FORWARD_UDP_OUTPUT = HDL_DIR / "eth_ip_forward_udp_8bit.sv"


def generate_eth_ip_parser() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=IP_PARSER,
        stream=STREAM_32,
        module_name="eth_ip_parser",
    )


def generate_eth_ip_forward_udp_8bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=IP_FORWARD_UDP_PARSER,
        stream=STREAM_8,
        module_name="eth_ip_forward_udp_8bit",
    )


def write_generated_file(generated: GeneratedFile, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generated.content)
    print(output)


def main() -> None:
    parser = ArgumentParser(description="Generate the Ethernet/IP parser SystemVerilog example.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=f"write generated SystemVerilog to a file, default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write generated SystemVerilog to the default HDL example path",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="write all generated SystemVerilog examples to the HDL example path",
    )
    parser.add_argument(
        "--forward-udp-8bit",
        action="store_true",
        help="generate the 8-bit AXI parser that forwards UDP payloads",
    )
    args = parser.parse_args()

    if args.all:
        write_generated_file(generate_eth_ip_parser(), DEFAULT_OUTPUT)
        write_generated_file(generate_eth_ip_forward_udp_8bit(), DEFAULT_FORWARD_UDP_OUTPUT)
        return

    generated = generate_eth_ip_forward_udp_8bit() if args.forward_udp_8bit else generate_eth_ip_parser()
    default_output = DEFAULT_FORWARD_UDP_OUTPUT if args.forward_udp_8bit else DEFAULT_OUTPUT
    output = args.output or (default_output if args.write else None)

    if output is None:
        print(generated.content, end="")
        return

    write_generated_file(generated, output)


if __name__ == "__main__":
    main()
