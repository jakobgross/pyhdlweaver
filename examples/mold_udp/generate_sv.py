"""
Generate SystemVerilog for the MoldUDP64 example parsers.

Run with --write to write all files, or pass a width flag for one variant.
"""
import sys
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.mold_udp.mold_udp import MOLD_UDP_PARSER
from pyhdlweaver.generators import GeneratedFile, SystemVerilogGenerator
from pyhdlweaver.stream.axi_stream import STREAM_8, STREAM_32, AxisStream

EXAMPLE_DIR = Path(__file__).resolve().parent
HDL_DIR = EXAMPLE_DIR / "hdl"
OUTPUT_8BIT = HDL_DIR / "mold_udp_8bit.sv"
OUTPUT_24BIT = HDL_DIR / "mold_udp_24bit.sv"
OUTPUT_32BIT = HDL_DIR / "mold_udp_32bit.sv"
OUTPUT_512BIT = HDL_DIR / "mold_udp_512bit.sv"


def generate_8bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=MOLD_UDP_PARSER,
        stream=STREAM_8,
        module_name="mold_udp_8bit",
    )


def generate_32bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=MOLD_UDP_PARSER,
        stream=STREAM_32,
        module_name="mold_udp_32bit",
    )


def generate_24bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=MOLD_UDP_PARSER,
        stream=AxisStream(data_width=24),
        module_name="mold_udp_24bit",
    )


def generate_512bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=MOLD_UDP_PARSER,
        stream=AxisStream(data_width=512),
        module_name="mold_udp_512bit",
    )


def write_generated_file(generated: GeneratedFile, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generated.content)
    print(output)


def main() -> None:
    parser = ArgumentParser(description="Generate the MoldUDP64 parser SystemVerilog examples.")
    parser.add_argument("--write", action="store_true", help="write files to hdl/")
    parser.add_argument("--all", action="store_true", help="write all variants")
    parser.add_argument("--8bit", dest="eight_bit", action="store_true")
    parser.add_argument("--24bit", dest="twenty_four_bit", action="store_true")
    parser.add_argument("--32bit", dest="thirty_two_bit", action="store_true")
    parser.add_argument("--512bit", dest="five_twelve_bit", action="store_true")
    args = parser.parse_args()

    if args.all:
        write_generated_file(generate_8bit(), OUTPUT_8BIT)
        write_generated_file(generate_24bit(), OUTPUT_24BIT)
        write_generated_file(generate_32bit(), OUTPUT_32BIT)
        write_generated_file(generate_512bit(), OUTPUT_512BIT)
        return

    if args.five_twelve_bit:
        generated = generate_512bit()
        default_output = OUTPUT_512BIT
    elif args.thirty_two_bit:
        generated = generate_32bit()
        default_output = OUTPUT_32BIT
    elif args.twenty_four_bit:
        generated = generate_24bit()
        default_output = OUTPUT_24BIT
    else:
        generated = generate_8bit()
        default_output = OUTPUT_8BIT

    output = default_output if args.write else None
    if output:
        write_generated_file(generated, output)
    else:
        print(generated.content, end="")


if __name__ == "__main__":
    main()
