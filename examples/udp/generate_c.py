"""Generate C headers for the UDP examples."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.udp.udp import UDP_CLASSIFIER_64, UDP_PORT_ROUTER
from pyhdlweaver.generators import CGenerator, GeneratedFile
from pyhdlweaver.stream.axi_stream import STREAM_8

OUT_DIR = Path(__file__).resolve().parent / "c"


def generated_files() -> tuple[GeneratedFile, ...]:
    generator = CGenerator()
    return (
        *generator.generate(UDP_PORT_ROUTER, STREAM_8, module_name="udp_port_router").files,
        *generator.generate(UDP_CLASSIFIER_64, STREAM_8, module_name="udp_classifier").files,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for generated in generated_files():
        output = OUT_DIR / generated.name
        output.write_text(generated.content)
        print(output)


if __name__ == "__main__":
    main()
