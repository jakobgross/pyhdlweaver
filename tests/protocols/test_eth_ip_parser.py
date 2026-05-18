from examples.eth_ip.eth_ip import (
    ETH_ETHERTYPE,
    ETH_HEADER_SIZE,
    ETH_IP_FIELDS,
    ETHERTYPE_IPV4,
    IP_HEADER_SIZE,
    IP_PARSER,
    IP_PAYLOAD_OFFSET,
    IP_PROTOCOL,
    IP_PROTO_UDP,
    IP_SRC,
    IP_TOTAL_LENGTH,
    IP_VERSION_IHL,
)
from pyhdlweaver.data_packet import DataPacket
from pyhdlweaver.protocols import SidebandProtocol
from pyhdlweaver.protocols.definitions import StreamLayout
from pyhdlweaver.stream.axi_stream import STREAM_8, STREAM_32, STREAM_64


def test_ip_parser_is_one_combined_ethernet_ipv4_parser():
    assert isinstance(IP_PARSER, SidebandProtocol)

    assert IP_PARSER.name == "eth_ip"
    assert IP_PARSER.next_protocol is None
    assert IP_PARSER.layers() == (IP_PARSER,)

    assert IP_PARSER.fields == tuple(ETH_IP_FIELDS)
    assert IP_PARSER.total_length == ETH_HEADER_SIZE + IP_HEADER_SIZE
    assert IP_PARSER.parse_length == IP_PAYLOAD_OFFSET
    assert not IP_PARSER.is_fixed_length


def test_ip_parser_fields_cover_ethernet_and_ipv4():
    assert ETHERTYPE_IPV4 == 0x0800

    assert ETH_ETHERTYPE in IP_PARSER.fields
    assert IP_PROTOCOL in IP_PARSER.fields
    assert IP_SRC in IP_PARSER.fields

    assert ETH_ETHERTYPE.offset == 12
    assert IP_PROTOCOL.offset == 23
    assert IP_SRC.offset == 26


def test_ip_parser_layout_uses_combined_frame_offsets():
    for stream in [STREAM_8, STREAM_32, STREAM_64]:
        layout = StreamLayout(stream, byte_offset=0)

        assert layout.header_beats(IP_PARSER.fields) == layout.header_beats(ETH_IP_FIELDS)
        assert layout.first_payload_beat(IP_PARSER.parse_length) == (
            layout.first_payload_beat(IP_PAYLOAD_OFFSET)
        )
        assert layout.field_beats(ETH_ETHERTYPE) == layout.field_beats(IP_PARSER.fields[0])


def test_ip_parser_eval_extracts_fields_from_packet_bytes():
    payload = bytes.fromhex("11223344556677889900")
    packet = DataPacket(
        bytes.fromhex(
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
        )
        + payload
    )

    values = IP_PARSER.eval(packet)

    assert values[ETH_ETHERTYPE.name] == ETHERTYPE_IPV4
    assert values[IP_VERSION_IHL.name] == 0x45
    assert values[IP_TOTAL_LENGTH.name] == 46
    assert values[IP_PROTOCOL.name] == IP_PROTO_UDP
    assert values[IP_SRC.name] == 0xC0A8010A
    assert values["data"] == payload
