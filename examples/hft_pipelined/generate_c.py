"""Generate C headers for the HFT pipeline stages."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.itch.itch import ITCH_PARSER
from examples.mold_udp.mold_udp import MOLD_UDP_PARSER
from examples.udp.udp import UDP_PORT_ROUTER
from pyhdlweaver.generators import CGenerator, GeneratedFile
from pyhdlweaver.stream.axi_stream import STREAM_8

OUT_DIR = Path(__file__).resolve().parent / "c"


def generated_files() -> tuple[GeneratedFile, ...]:
    generator = CGenerator()
    return (
        *generator.generate(UDP_PORT_ROUTER, STREAM_8, module_name="hft_udp_port_router").files,
        *generator.generate(MOLD_UDP_PARSER, STREAM_8, module_name="hft_mold_udp").files,
        *generator.generate(ITCH_PARSER, STREAM_8, module_name="hft_itch_parser").files,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for generated in generated_files():
        output = OUT_DIR / generated.name
        output.write_text(generated.content)
        print(output)


if __name__ == "__main__":
    main()
