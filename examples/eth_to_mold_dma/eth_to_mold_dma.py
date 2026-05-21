"""
ETH/IP/UDP/MoldUDP splitter for DMA.

Full Ethernet frames enter on AXI-Stream. The parser accepts IPv4 UDP packets
for a configured destination port, parses the MoldUDP64 envelope, and forwards
each length-prefixed Mold message as one AXI-Stream frame.
"""
from pyhdlweaver.actions import DropOnMismatch, DropOnRegisterMismatch
from pyhdlweaver.protocols import LengthPrefixedProtocol, MultiMessageProtocol
from pyhdlweaver.protocols.definitions.field import Field

ETH_ETHERTYPE = Field("eth_ethertype", offset=12, width=16).with_actions(
    DropOnMismatch(expected=0x0800, counter="non_ipv4_drop_count"),
)
IP_PROTOCOL = Field("ip_protocol", offset=23, width=8).with_actions(
    DropOnMismatch(expected=0x11, counter="non_udp_drop_count"),
)
UDP_DST_PORT = Field("udp_dst_port", offset=36, width=16).with_actions(
    DropOnRegisterMismatch(
        register="expected_dst_port",
        default_value=4789,
        counter="wrong_port_drop_count",
    ),
)
MOLD_SESSION_ID = Field("mold_session_id", offset=42, width=80)
MOLD_SEQ_NUM = Field("mold_seq_num", offset=52, width=64)
MOLD_MSG_COUNT = Field("mold_msg_count", offset=60, width=16)

OUTER_HEADER_BYTES = 62
MSG_LEN_FIELD = Field("msg_len", offset=0, width=16)

ETH_TO_MOLD_DMA = MultiMessageProtocol(
    name="eth_to_mold_dma",
    fields=[
        ETH_ETHERTYPE,
        IP_PROTOCOL,
        UDP_DST_PORT,
        MOLD_SESSION_ID,
        MOLD_SEQ_NUM,
        MOLD_MSG_COUNT,
    ],
    total_length=OUTER_HEADER_BYTES,
    message_count_field="mold_msg_count",
    sub_protocol=LengthPrefixedProtocol(
        name="mold_message",
        fields=[MSG_LEN_FIELD],
        total_length=MSG_LEN_FIELD.width_bytes,
        length_field=MSG_LEN_FIELD,
    ),
)
