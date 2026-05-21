"""
All-in-one HFT parser: ETH + IP + UDP + MoldUDP64 + ITCH 5.0 in a single FSM.

Outer header (62 bytes, fixed offsets from start of Ethernet frame):
  Ethernet  offset  0: dst_mac (6), src_mac (6), ethertype (2)
  IPv4      offset 14: version_ihl (1), ... protocol (1 @ 23), ... dst_ip (4 @ 30)
  UDP       offset 34: src_port (2), dst_port (2 @ 36), length (2), checksum (2)
  MoldUDP64 offset 42: session_id (10), seq_num (8), msg_count (2 @ 60)

Each sub-message:
  msg_len (2 bytes) then ITCH 5.0 payload (msg_len bytes)
  ITCH message_type at payload offset 0 selects the variant.

The UDP destination port is exposed as an AXI-Lite configuration register so
the expected multicast port can be set at boot time.
"""
from pyhdlweaver.actions import DropOnMismatch, DropOnRegisterMismatch
from pyhdlweaver.protocols import LengthPrefixedDiscriminatedSubProtocol, MultiMessageProtocol
from pyhdlweaver.protocols.definitions.field import Field
from examples.itch.itch import ITCH_PARSER

ETH_ETHERTYPE  = Field("eth_ethertype",  offset=12, width=16).with_actions(
    DropOnMismatch(expected=0x0800, counter="non_ipv4_drop_count"),
)
IP_PROTOCOL    = Field("ip_protocol",    offset=23, width=8).with_actions(
    DropOnMismatch(expected=0x11, counter="non_udp_drop_count"),
)
UDP_DST_PORT   = Field("udp_dst_port",   offset=36, width=16).with_actions(
    DropOnRegisterMismatch(
        register="expected_dst_port",
        default_value=4789,
        mask=None,
        counter="wrong_port_drop_count",
    ),
)
MOLD_SESSION_ID = Field("mold_session_id", offset=42, width=80)
MOLD_SEQ_NUM    = Field("mold_seq_num",    offset=52, width=64)
MOLD_MSG_COUNT  = Field("mold_msg_count",  offset=60, width=16)

OUTER_HEADER_BYTES = 62  # 14 (ETH) + 20 (IP) + 8 (UDP) + 20 (MoldUDP)

MSG_LEN_FIELD = Field("msg_len", offset=0, width=16)

ALL_IN_ONE_HFT_PARSER = MultiMessageProtocol(
    name="all_in_one_hft",
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
    sub_protocol=LengthPrefixedDiscriminatedSubProtocol(
        name="itch_message",
        length_field=MSG_LEN_FIELD,
        discriminated=ITCH_PARSER,
    ),
)
