"""
MoldUDP64 protocol definitions used as generator inputs.

MoldUDP64 outer header (20 bytes):
  session_id  : 10 bytes, offset 0
  seq_num     : 8 bytes,  offset 10
  msg_count   : 2 bytes,  offset 18

Each message is a 2-byte length prefix followed by msg_len bytes of payload.
"""
import struct

from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols.length_prefixed_protocol import LengthPrefixedProtocol
from pyhdlweaver.protocols.multi_message_protocol import MultiMessageProtocol

# Outer header fields.
MOLD_SESSION_ID = Field("session_id", offset=0,  width=80)  # 10 bytes
MOLD_SEQ_NUM    = Field("seq_num",    offset=10, width=64)  # 8 bytes
MOLD_MSG_COUNT  = Field("msg_count",  offset=18, width=16)  # 2 bytes

MOLD_OUTER_HEADER_SIZE = 20

# Sub-protocol: 2-byte length prefix per message, no additional header fields.
MOLD_MESSAGE_LENGTH_FIELD = Field("msg_len", offset=0, width=16)

MOLD_MESSAGE_SUB_PROTOCOL = LengthPrefixedProtocol(
    name="mold_message",
    fields=[MOLD_MESSAGE_LENGTH_FIELD],
    length_field=MOLD_MESSAGE_LENGTH_FIELD,
)

MOLD_UDP_PARSER = MultiMessageProtocol(
    name="mold_udp",
    fields=[MOLD_SESSION_ID, MOLD_SEQ_NUM, MOLD_MSG_COUNT],
    total_length=MOLD_OUTER_HEADER_SIZE,
    message_count_field="msg_count",
    sub_protocol=MOLD_MESSAGE_SUB_PROTOCOL,
)


def make_mold_udp_payload(session_id: bytes, seq_num: int, messages: list[bytes]) -> bytes:
    """Build a raw MoldUDP64 payload (no UDP/IP/Ethernet headers)."""
    assert len(session_id) == 10
    msg_count = len(messages)
    header = session_id + struct.pack(">QH", seq_num, msg_count)
    body = b"".join(struct.pack(">H", len(m)) + m for m in messages)
    return header + body
