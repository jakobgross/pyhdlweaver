import ctypes
import struct
from pathlib import Path

SO_PATH = Path(__file__).with_name("all_in_one_hft.so")
SESSION_ID = b"SESSIONID_"
DEFAULT_PORT = 4789


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


class AllInOneHftConfig(ctypes.Structure):
    _fields_ = [("expected_dst_port", ctypes.c_uint16)]


class AllInOneHftMessage(ctypes.Structure):
    _fields_ = [
        ("msg_len", ctypes.c_uint16),
        ("payload", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
    ]


class AllInOneHftResult(ctypes.Structure):
    _fields_ = [
        ("eth_ethertype", ctypes.c_uint16),
        ("ip_protocol", ctypes.c_uint8),
        ("udp_dst_port", ctypes.c_uint16),
        ("mold_session_id", ctypes.c_uint8 * 10),
        ("mold_seq_num", ctypes.c_uint64),
        ("mold_msg_count", ctypes.c_uint16),
        ("message_count", ctypes.c_size_t),
        ("parsed_message_count", ctypes.c_size_t),
        ("messages", AllInOneHftMessage * 64),
        ("forwarded", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
        ("has_destination", ctypes.c_bool),
        ("destination", ctypes.c_uint32),
    ]


def load_parser() -> ctypes.CDLL:
    lib = ctypes.CDLL(str(SO_PATH))
    lib.all_in_one_hft_parse.argtypes = [ByteSlice, ctypes.POINTER(AllInOneHftConfig)]
    lib.all_in_one_hft_parse.restype = AllInOneHftResult
    lib.all_in_one_hft_default_config.argtypes = []
    lib.all_in_one_hft_default_config.restype = AllInOneHftConfig
    return lib


def _ip_header(ip_proto: int, udp_len: int) -> bytes:
    total_len = 20 + udp_len
    return struct.pack(
        ">BBHHHBBHII",
        0x45, 0x00, total_len,
        0x0000, 0x0000,
        64, ip_proto, 0x0000,
        0xC0A80102, 0xC0A80101,
    )


def make_frame(
    messages: list[bytes],
    dst_port: int = DEFAULT_PORT,
    ethertype: int = 0x0800,
    ip_proto: int = 0x11,
    seq_num: int = 1,
) -> bytes:
    mold_payload = SESSION_ID + struct.pack(">QH", seq_num, len(messages))
    for msg in messages:
        mold_payload += struct.pack(">H", len(msg)) + msg
    udp_payload = mold_payload
    udp_len = 8 + len(udp_payload)
    udp = struct.pack(">HHHH", 12345, dst_port, udp_len, 0) + udp_payload
    eth = b"\xff\xff\xff\xff\xff\xff\xaa\xbb\xcc\xdd\xee\xff" + struct.pack(">H", ethertype)
    return eth + _ip_header(ip_proto, len(udp)) + udp


def test_outer_header_fields_are_parsed():
    lib = load_parser()
    frame = make_frame([b"hello", b"world"], seq_num=42)
    _buf, inp = as_input(frame)
    result = lib.all_in_one_hft_parse(inp, None)

    assert result.ok
    assert result.eth_ethertype == 0x0800
    assert result.ip_protocol == 0x11
    assert result.udp_dst_port == DEFAULT_PORT
    assert bytes(result.mold_session_id) == SESSION_ID
    assert result.mold_seq_num == 42
    assert result.mold_msg_count == 2


def test_sub_messages_are_exposed_as_payloads():
    lib = load_parser()
    frame = make_frame([b"hello", b"world"])
    _buf, inp = as_input(frame)
    result = lib.all_in_one_hft_parse(inp, None)

    assert result.ok
    assert result.parsed_message_count == 2
    assert result.messages[0].msg_len == 5
    assert slice_bytes(result.messages[0].payload) == b"hello"
    assert result.messages[1].msg_len == 5
    assert slice_bytes(result.messages[1].payload) == b"world"


def test_non_ipv4_frame_is_dropped():
    lib = load_parser()
    frame = make_frame([b"data"], ethertype=0x86DD)
    _buf, inp = as_input(frame)
    result = lib.all_in_one_hft_parse(inp, None)

    assert not result.ok
    assert result.error_flags & (1 << 1)


def test_non_udp_frame_is_dropped():
    lib = load_parser()
    frame = make_frame([b"data"], ip_proto=0x06)
    _buf, inp = as_input(frame)
    result = lib.all_in_one_hft_parse(inp, None)

    assert not result.ok
    assert result.error_flags & (1 << 1)


def test_wrong_port_is_dropped_with_default_config():
    lib = load_parser()
    frame = make_frame([b"data"], dst_port=9999)
    _buf, inp = as_input(frame)
    result = lib.all_in_one_hft_parse(inp, None)

    assert not result.ok
    assert result.error_flags & (1 << 1)


def test_custom_config_allows_different_port():
    lib = load_parser()
    frame = make_frame([b"data"], dst_port=9999)
    _buf, inp = as_input(frame)
    cfg = AllInOneHftConfig(expected_dst_port=9999)
    result = lib.all_in_one_hft_parse(inp, ctypes.byref(cfg))

    assert result.ok
    assert result.udp_dst_port == 9999


def test_short_frame_sets_error_flag():
    lib = load_parser()
    _buf, inp = as_input(b"\x00" * 30)
    result = lib.all_in_one_hft_parse(inp, None)

    assert not result.ok
    assert result.error_flags & (1 << 0)
