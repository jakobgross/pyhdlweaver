import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.eth_ip.eth_ip import ETH_IP_FIELDS, IP_PARSER
from pyhdlweaver.protocols.definitions import StreamLayout
from pyhdlweaver.stream.axi_stream import STREAM_8, STREAM_32, STREAM_64


def main() -> None:
    for stream in [STREAM_8, STREAM_32, STREAM_64]:
        layout = StreamLayout(stream, byte_offset=0)
        print(layout.report(ETH_IP_FIELDS))
        print(f"  Parse beats  : {layout.header_beats(IP_PARSER.fields)}")
        print(f"  Payload from : beat {layout.first_payload_beat(IP_PARSER.parse_length)}")
        print()


if __name__ == "__main__":
    main()
