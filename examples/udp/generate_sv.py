"""
Generate SystemVerilog for the UDP example parsers.

Run without flags to print both generated files to stdout, or pass specific flags
(--udp-port-router-8bit, --udp-classifier-64bit) combined with --write to write
the selected file to examples/udp/hdl/.
"""
import sys
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.udp.udp import UDP_CLASSIFIER_64, UDP_PORT_ROUTER
from pyhdlweaver.generators import GeneratedFile, SystemVerilogGenerator
from pyhdlweaver.stream.axi_stream import STREAM_64, STREAM_8

EXAMPLE_DIR = Path(__file__).resolve().parent
HDL_DIR = EXAMPLE_DIR / "hdl"

OUTPUTS = {
    "udp_port_router_8bit": HDL_DIR / "udp_port_router_8bit.sv",
    "udp_classifier_64bit": HDL_DIR / "udp_classifier_64bit.sv",
}


def generate_udp_port_router_8bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=UDP_PORT_ROUTER,
        stream=STREAM_8,
        module_name="udp_port_router_8bit",
    )


def generate_udp_classifier_64bit() -> GeneratedFile:
    return SystemVerilogGenerator().generate(
        protocol=UDP_CLASSIFIER_64,
        stream=STREAM_64,
        module_name="udp_classifier_64bit",
    )


def write_generated_file(generated: GeneratedFile, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generated.content)
    print(output)


def main() -> None:
    parser = ArgumentParser(description="Generate UDP SystemVerilog examples.")
    parser.add_argument(
        "--udp-port-router-8bit",
        action="store_true",
        help="generate udp_port_router_8bit",
    )
    parser.add_argument(
        "--udp-classifier-64bit",
        action="store_true",
        help="generate udp_classifier_64bit",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write generated files to the default HDL example paths",
    )
    args = parser.parse_args()

    targets: list[tuple[str, GeneratedFile]] = []
    if args.udp_port_router_8bit:
        targets.append(("udp_port_router_8bit", generate_udp_port_router_8bit()))
    if args.udp_classifier_64bit:
        targets.append(("udp_classifier_64bit", generate_udp_classifier_64bit()))
    if not targets:
        targets = [
            ("udp_port_router_8bit", generate_udp_port_router_8bit()),
            ("udp_classifier_64bit", generate_udp_classifier_64bit()),
        ]

    for name, generated in targets:
        if args.write:
            write_generated_file(generated, OUTPUTS[name])
        else:
            print(generated.content, end="")


if __name__ == "__main__":
    main()
