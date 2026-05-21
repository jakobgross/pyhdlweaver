"""Generate SystemVerilog for the ETH to Mold DMA example."""
import sys
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.eth_to_mold_dma.eth_to_mold_dma import ETH_TO_MOLD_DMA
from pyhdlweaver.generators import GeneratedFile, SystemVerilogGenerator
from pyhdlweaver.stream.axi_stream import STREAM_64

EXAMPLE_DIR = Path(__file__).resolve().parent
HDL_DIR = EXAMPLE_DIR / "hdl"
DEFAULT_OUTPUT = HDL_DIR / "eth_to_mold_dma_64bit.sv"


def generate_64bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        ETH_TO_MOLD_DMA,
        STREAM_64,
        module_name="eth_to_mold_dma_64bit",
    )


def write_generated_file(generated: GeneratedFile, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generated.content)
    print(output)


def main() -> None:
    parser = ArgumentParser(description="Generate the ETH to Mold DMA SystemVerilog example.")
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
    args = parser.parse_args()

    generated = generate_64bit()
    output = args.output or (DEFAULT_OUTPUT if args.write else None)
    if output is None:
        print(generated.content, end="")
        return

    write_generated_file(generated, output)


if __name__ == "__main__":
    main()
