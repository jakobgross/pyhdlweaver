"""
Generate SystemVerilog for the ITCH 5.0 discriminated-protocol parser example.

Run with --write to write all files, or pass a width flag for one variant.

Hardware behaviour of the generated parser
------------------------------------------
Fields that appear in multiple variants at the same byte offset are represented
by a single Field object shared across those variants. The hardware captures all
of them unconditionally on each beat, so every output port is always driven.
Downstream logic uses the message_type output to decide which fields are
meaningful for the received message.

Fields whose same semantic concept lives at different byte offsets in different
message types (e.g. stock at offset 11 in admin messages vs order_stock at
offset 24 in order messages) are given distinct names and get their own
registers and ports.
"""
import sys
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.itch.itch import ITCH_PARSER
from pyhdlweaver.generators import GeneratedFile, SystemVerilogGenerator
from pyhdlweaver.stream.axi_stream import AxisStream

EXAMPLE_DIR = Path(__file__).resolve().parent
HDL_DIR = EXAMPLE_DIR / "hdl"
OUTPUT_8BIT  = HDL_DIR / "itch_parser_8bit.sv"
OUTPUT_32BIT = HDL_DIR / "itch_parser_32bit.sv"
OUTPUT_64BIT = HDL_DIR / "itch_parser_64bit.sv"


def generate_8bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=ITCH_PARSER,
        stream=AxisStream(data_width=8),
        module_name="itch_parser_8bit",
    )


def generate_32bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=ITCH_PARSER,
        stream=AxisStream(data_width=32),
        module_name="itch_parser_32bit",
    )


def generate_64bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=ITCH_PARSER,
        stream=AxisStream(data_width=64),
        module_name="itch_parser_64bit",
    )


def write_generated_file(generated: GeneratedFile, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generated.content)
    print(output)


def main() -> None:
    parser = ArgumentParser(description="Generate ITCH 5.0 discriminated parser SystemVerilog.")
    parser.add_argument("--write", action="store_true", help="write files to hdl/")
    parser.add_argument("--all", action="store_true", help="write all variants")
    parser.add_argument("--8bit",  dest="eight_bit",     action="store_true")
    parser.add_argument("--32bit", dest="thirty_two_bit", action="store_true")
    parser.add_argument("--64bit", dest="sixty_four_bit", action="store_true")
    args = parser.parse_args()

    if args.all:
        write_generated_file(generate_8bit(),  OUTPUT_8BIT)
        write_generated_file(generate_32bit(), OUTPUT_32BIT)
        write_generated_file(generate_64bit(), OUTPUT_64BIT)
        return

    if args.sixty_four_bit:
        generated, default_output = generate_64bit(), OUTPUT_64BIT
    elif args.thirty_two_bit:
        generated, default_output = generate_32bit(), OUTPUT_32BIT
    else:
        generated, default_output = generate_8bit(), OUTPUT_8BIT

    output = default_output if args.write else None
    if output:
        write_generated_file(generated, output)
    else:
        print(generated.content, end="")


if __name__ == "__main__":
    main()
