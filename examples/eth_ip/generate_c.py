"""Generate C headers for the Ethernet/IP examples."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.eth_ip.eth_ip import IP_FORWARD_UDP_PARSER, IP_PARSER, IP_ROUTE_BROADCAST_UDP_PARSER
from pyhdlweaver.generators import CGenerator, GeneratedFile
from pyhdlweaver.stream.axi_stream import STREAM_8

OUT_DIR = Path(__file__).resolve().parent / "c"


def generated_files() -> tuple[GeneratedFile, ...]:
    generator = CGenerator()
    return (
        *generator.generate(IP_PARSER, STREAM_8, module_name="eth_ip_parser").files,
        *generator.generate(IP_FORWARD_UDP_PARSER, STREAM_8, module_name="eth_ip_forward_udp").files,
        *generator.generate(IP_ROUTE_BROADCAST_UDP_PARSER, STREAM_8, module_name="eth_ip_route_broadcast_udp").files,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for generated in generated_files():
        output = OUT_DIR / generated.name
        output.write_text(generated.content)
        print(output)


if __name__ == "__main__":
    main()
