import ctypes
from pathlib import Path

SO_PATH = Path(__file__).with_name("itch_parser.so")

MSG_SYSTEM_EVENT = 0x53
MSG_ADD_ORDER = 0x41
EVENT_START_SYS_HOURS = ord("S")
BUY = ord("B")


class ByteSlice(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_uint8)),
        ("length", ctypes.c_size_t),
    ]


def as_input(data: bytes) -> tuple[ctypes.Array, ByteSlice]:
    buffer = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
    return buffer, ByteSlice(buffer, len(data))


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


def load_parser() -> ctypes.CDLL:
    lib = ctypes.CDLL(str(SO_PATH))
    lib.itch_parser_parse.argtypes = [ByteSlice, ctypes.POINTER(ItchConfig)]
    lib.itch_parser_parse.restype = ItchResult
    return lib


def make_header(msg_type: int, stock_locate: int = 1, tracking_number: int = 100, timestamp: int = 12345) -> bytes:
    return (
        bytes([msg_type])
        + stock_locate.to_bytes(2, "big")
        + tracking_number.to_bytes(2, "big")
        + timestamp.to_bytes(6, "big")
    )


def make_system_event(event_code: int) -> bytes:
    return make_header(MSG_SYSTEM_EVENT) + bytes([event_code])


def make_add_order(order_ref: int, shares: int, stock: bytes, price: int) -> bytes:
    return (
        make_header(MSG_ADD_ORDER)
        + order_ref.to_bytes(8, "big")
        + bytes([BUY])
        + shares.to_bytes(4, "big")
        + stock
        + price.to_bytes(4, "big")
    )


def test_parses_system_event_message():
    lib = load_parser()
    message = make_system_event(EVENT_START_SYS_HOURS)
    _buffer, input_view = as_input(message)
    result = lib.itch_parser_parse(input_view, None)

    assert result.ok
    assert result.message_type == MSG_SYSTEM_EVENT
    assert result.variant == MSG_SYSTEM_EVENT
    assert result.data.variant_53.event_code == EVENT_START_SYS_HOURS


def test_parses_add_order_message():
    lib = load_parser()
    order_ref = 0x0123456789ABCDEF
    stock = b"PYHDL   "
    message = make_add_order(order_ref=order_ref, shares=1000, stock=stock, price=1_500_000)
    _buffer, input_view = as_input(message)
    result = lib.itch_parser_parse(input_view, None)

    assert result.ok
    assert result.message_type == MSG_ADD_ORDER
    assert result.data.variant_41.order_reference_number == order_ref
    assert result.data.variant_41.buy_sell_indicator == BUY
    assert result.data.variant_41.shares == 1000
    assert result.data.variant_41.order_stock == int.from_bytes(stock, "big")
    assert result.data.variant_41.price == 1_500_000


def test_unknown_message_type_sets_error():
    lib = load_parser()
    message = make_header(0x01) + b"extra"
    _buffer, input_view = as_input(message)
    result = lib.itch_parser_parse(input_view, None)

    assert not result.ok
    assert result.variant == 0
    assert result.error_flags & (1 << 2)
