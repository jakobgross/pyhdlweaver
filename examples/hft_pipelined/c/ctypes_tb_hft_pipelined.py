import ctypes
import struct
from pathlib import Path

SO_DIR = Path(__file__).resolve().parent
ITCH_UDP_PORT = 12001
SESSION_ID = b"SESSIONID_"
MSG_SYSTEM_EVENT = 0x53
MSG_ADD_ORDER = 0x41
EVENT_START_OF_MESSAGES = ord("O")
BUY = ord("B")


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


def bytes_to_input(data: bytes) -> tuple[ctypes.Array, ByteSlice]:
    return as_input(data)


def _ip_header(ip_proto: int, total_len: int) -> bytes:
    return struct.pack(
        ">BBHHHBBHII",
        0x45,
        0x00,
        total_len,
        0x1234,
        0x0000,
        64,
        ip_proto,
        0x0000,
        0xC0A80102,
        0xC0A80101,
    )


def _eth_ip_udp(dst_port: int, udp_payload: bytes) -> bytes:
    eth = b"\xff\xff\xff\xff\xff\xff\x11\x22\x33\x44\x55\x66\x08\x00"
    udp_len = 8 + len(udp_payload)
    udp = struct.pack(">HHHH", 12345, dst_port, udp_len, 0) + udp_payload
    return eth + _ip_header(0x11, 20 + len(udp)) + udp


def _mold_outer(seq_num: int, msg_count: int) -> bytes:
    return SESSION_ID + struct.pack(">QH", seq_num, msg_count)


def _mold_submsg(body: bytes) -> bytes:
    return struct.pack(">H", len(body)) + body


def make_frame(seq_num: int, messages: list[bytes], dst_port: int = ITCH_UDP_PORT) -> bytes:
    mold = _mold_outer(seq_num, len(messages)) + b"".join(_mold_submsg(message) for message in messages)
    return _eth_ip_udp(dst_port, mold)


def make_itch_header(msg_type: int, stock_locate: int = 1, tracking_number: int = 100, timestamp: int = 1000) -> bytes:
    return (
        bytes([msg_type])
        + stock_locate.to_bytes(2, "big")
        + tracking_number.to_bytes(2, "big")
        + timestamp.to_bytes(6, "big")
    )


def make_system_event(event_code: int, **kwargs) -> bytes:
    return make_itch_header(MSG_SYSTEM_EVENT, **kwargs) + bytes([event_code])


def make_add_order(order_ref: int, shares: int, stock: bytes, price: int, **kwargs) -> bytes:
    return (
        make_itch_header(MSG_ADD_ORDER, **kwargs)
        + order_ref.to_bytes(8, "big")
        + bytes([BUY])
        + shares.to_bytes(4, "big")
        + stock
        + price.to_bytes(4, "big")
    )


class UdpConfig(ctypes.Structure):
    _fields_ = [("dst_port", ctypes.c_uint16)]


class UdpResult(ctypes.Structure):
    _fields_ = [
        ("udp_dport", ctypes.c_uint16),
        ("udp_length", ctypes.c_uint16),
        ("udp_checksum", ctypes.c_uint16),
        ("forwarded", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
        ("has_destination", ctypes.c_bool),
        ("destination", ctypes.c_uint32),
    ]


class MoldConfig(ctypes.Structure):
    _fields_ = [("unused", ctypes.c_uint8)]


class MoldMessage(ctypes.Structure):
    _fields_ = [
        ("msg_len", ctypes.c_uint16),
        ("payload", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
    ]


class MoldResult(ctypes.Structure):
    _fields_ = [
        ("session_id", ctypes.c_uint8 * 10),
        ("seq_num", ctypes.c_uint64),
        ("msg_count", ctypes.c_uint16),
        ("message_count", ctypes.c_size_t),
        ("parsed_message_count", ctypes.c_size_t),
        ("messages", MoldMessage * 64),
        ("forwarded", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
        ("has_destination", ctypes.c_bool),
        ("destination", ctypes.c_uint32),
    ]


class ItchConfig(ctypes.Structure):
    _fields_ = [("unused", ctypes.c_uint8)]


class ItchVariant53(ctypes.Structure):
    _fields_ = [("event_code", ctypes.c_uint8)]


class ItchVariant41(ctypes.Structure):
    _fields_ = [
        ("order_reference_number", ctypes.c_uint64),
        ("buy_sell_indicator", ctypes.c_uint8),
        ("shares", ctypes.c_uint32),
        ("order_stock", ctypes.c_uint64),
        ("price", ctypes.c_uint32),
    ]


class ItchVariantData(ctypes.Union):
    _fields_ = [
        ("variant_53", ItchVariant53),
        ("variant_41", ItchVariant41),
        ("raw", ctypes.c_uint64 * 6),
    ]


class ItchResult(ctypes.Structure):
    _fields_ = [
        ("message_type", ctypes.c_uint8),
        ("stock_locate", ctypes.c_uint16),
        ("tracking_number", ctypes.c_uint16),
        ("timestamp", ctypes.c_uint64),
        ("variant", ctypes.c_int),
        ("data", ItchVariantData),
        ("forwarded", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
        ("has_destination", ctypes.c_bool),
        ("destination", ctypes.c_uint32),
    ]


def load_udp() -> ctypes.CDLL:
    lib = ctypes.CDLL(str(SO_DIR / "hft_udp_port_router.so"))
    lib.hft_udp_port_router_parse.argtypes = [ByteSlice, ctypes.POINTER(UdpConfig)]
    lib.hft_udp_port_router_parse.restype = UdpResult
    return lib


def load_mold() -> ctypes.CDLL:
    lib = ctypes.CDLL(str(SO_DIR / "hft_mold_udp.so"))
    lib.hft_mold_udp_parse.argtypes = [ByteSlice, ctypes.POINTER(MoldConfig)]
    lib.hft_mold_udp_parse.restype = MoldResult
    return lib


def load_itch() -> ctypes.CDLL:
    lib = ctypes.CDLL(str(SO_DIR / "hft_itch_parser.so"))
    lib.hft_itch_parser_parse.argtypes = [ByteSlice, ctypes.POINTER(ItchConfig)]
    lib.hft_itch_parser_parse.restype = ItchResult
    return lib


def run_pipeline(frame: bytes, dst_port: int = ITCH_UDP_PORT) -> tuple[UdpResult, MoldResult, list[ItchResult]]:
    udp = load_udp()
    mold = load_mold()
    itch = load_itch()

    udp_config = UdpConfig(dst_port=dst_port)
    frame_buffer, frame_input = bytes_to_input(frame)
    udp_result = udp.hft_udp_port_router_parse(frame_input, ctypes.byref(udp_config))

    mold_payload = slice_bytes(udp_result.forwarded)
    mold_buffer, mold_input = bytes_to_input(mold_payload)
    mold_result = mold.hft_mold_udp_parse(mold_input, None)

    itch_results = []
    for index in range(mold_result.parsed_message_count):
        message = slice_bytes(mold_result.messages[index].payload)
        message_buffer, message_input = bytes_to_input(message)
        itch_results.append(itch.hft_itch_parser_parse(message_input, None))
        del message_buffer

    del frame_buffer, mold_buffer
    return udp_result, mold_result, itch_results


def test_pipeline_parses_two_itch_messages():
    order_ref = 0x0123456789ABCDEF
    messages = [
        make_system_event(EVENT_START_OF_MESSAGES, stock_locate=1, tracking_number=10, timestamp=1000),
        make_add_order(order_ref, shares=500, stock=b"AAPL    ", price=1_500_000, stock_locate=2, tracking_number=20),
    ]
    frame = make_frame(seq_num=7, messages=messages)

    udp_result, mold_result, itch_results = run_pipeline(frame)

    assert udp_result.ok
    assert udp_result.destination == 0
    assert mold_result.ok
    assert mold_result.seq_num == 7
    assert mold_result.parsed_message_count == 2
    assert itch_results[0].ok
    assert itch_results[0].message_type == MSG_SYSTEM_EVENT
    assert itch_results[0].data.variant_53.event_code == EVENT_START_OF_MESSAGES
    assert itch_results[1].ok
    assert itch_results[1].message_type == MSG_ADD_ORDER
    assert itch_results[1].data.variant_41.order_reference_number == order_ref
    assert itch_results[1].data.variant_41.shares == 500


def test_pipeline_routes_wrong_udp_port_to_default_destination():
    message = make_system_event(EVENT_START_OF_MESSAGES)
    frame = make_frame(seq_num=8, messages=[message], dst_port=9999)

    udp_result, mold_result, itch_results = run_pipeline(frame)

    assert udp_result.ok
    assert udp_result.destination == 1
    assert mold_result.ok
    assert itch_results[0].ok


def test_pipeline_reports_unknown_itch_type():
    unknown = make_itch_header(0x01) + b"extra"
    frame = make_frame(seq_num=9, messages=[unknown])

    udp_result, mold_result, itch_results = run_pipeline(frame)

    assert udp_result.ok
    assert mold_result.ok
    assert not itch_results[0].ok
    assert itch_results[0].error_flags & (1 << 2)
