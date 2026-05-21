import ctypes
import struct
from pathlib import Path

from examples.mold_udp.mold_udp import make_mold_udp_payload

SO_PATH = Path(__file__).with_name("mold_udp.so")
SESSION_ID = b"SESSIONID_"


class ByteSlice(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_uint8)),
        ("length", ctypes.c_size_t),
    ]


def as_input(data: bytes) -> tuple[ctypes.Array, ByteSlice]:
    buffer = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
    return buffer, ByteSlice(buffer, len(data))


def slice_bytes(view: ByteSlice) -> bytes:
    if not view.data or view.length == 0:
        return b""
    return ctypes.string_at(view.data, view.length)


class MoldUdpConfig(ctypes.Structure):
    _fields_ = [("unused", ctypes.c_uint8)]


class MoldUdpMessage(ctypes.Structure):
    _fields_ = [
        ("msg_len", ctypes.c_uint16),
        ("payload", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
    ]


class MoldUdpResult(ctypes.Structure):
    _fields_ = [
        ("session_id", ctypes.c_uint8 * 10),
        ("seq_num", ctypes.c_uint64),
        ("msg_count", ctypes.c_uint16),
        ("message_count", ctypes.c_size_t),
        ("parsed_message_count", ctypes.c_size_t),
        ("messages", MoldUdpMessage * 64),
        ("forwarded", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
        ("has_destination", ctypes.c_bool),
        ("destination", ctypes.c_uint32),
    ]


def load_parser() -> ctypes.CDLL:
    lib = ctypes.CDLL(str(SO_PATH))
    lib.mold_udp_parse.argtypes = [ByteSlice, ctypes.POINTER(MoldUdpConfig)]
    lib.mold_udp_parse.restype = MoldUdpResult
    return lib


def test_two_messages_are_returned_as_array_entries():
    lib = load_parser()
    payload = make_mold_udp_payload(SESSION_ID, seq_num=10, messages=[b"hello", b"world"])
    _buffer, input_view = as_input(payload)
    result = lib.mold_udp_parse(input_view, None)

    assert result.ok
    assert bytes(result.session_id) == SESSION_ID
    assert result.seq_num == 10
    assert result.msg_count == 2
    assert result.parsed_message_count == 2
    assert slice_bytes(result.messages[0].payload) == b"hello"
    assert slice_bytes(result.messages[1].payload) == b"world"


def test_truncated_message_sets_error_flags():
    lib = load_parser()
    payload = SESSION_ID + struct.pack(">QH", 11, 1) + struct.pack(">H", 8) + b"abc"
    _buffer, input_view = as_input(payload)
    result = lib.mold_udp_parse(input_view, None)

    assert not result.ok
    assert result.error_flags & (1 << 4)
    assert result.messages[0].error_flags & (1 << 4)
