import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.eth_ip.eth_ip import IP_PARSER
from pyhdlweaver.data_packet import DataPacket


SAMPLE_ETH_IP_PACKET = bytes.fromhex(
    "001122334455"
    "66778899aabb"
    "0800"
    "4500"
    "002e"
    "1234"
    "4000"
    "4011"
    "0000"
    "c0a8010a"
    "c0a80114"
    "11223344556677889900"
)


def main() -> None:
    values = IP_PARSER.eval(DataPacket(SAMPLE_ETH_IP_PACKET))

    print(f"Parser: {IP_PARSER.name}")
    for field in IP_PARSER.fields:
        value = values[field.name]
        width_digits = max(1, (field.width + 3) // 4)
        print(f"{field.name:<18} 0x{value:0{width_digits}x}")

    print(f"{'data':<18} {values['data'].hex()}")


if __name__ == "__main__":
    main()
