import struct

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSource

CLOCK_PERIOD_NS = 10

DEFAULT_SRC_IP = 0xC0A80102
DEFAULT_DST_IP = 0xC0A80101
ITCH_UDP_PORT  = 12001
OTHER_UDP_PORT = 9999

SESSION_ID = b"SESSIONID_"

MSG_SYSTEM_EVENT = 0x53
MSG_ADD_ORDER    = 0x41
MSG_ORDER_DELETE = 0x44
UNKNOWN_TYPE     = 0xFF

BUY = ord('B')
EVENT_START_OF_MESSAGES = ord('O')
EVENT_END_OF_MESSAGES   = ord('C')


def _ip_header(ip_proto: int, total_len: int) -> bytes:
    return struct.pack(
        ">BBHHHBBHII",
        0x45, 0x00, total_len,
        0x1234, 0x0000,
        64, ip_proto, 0x0000,
        DEFAULT_SRC_IP, DEFAULT_DST_IP,
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


def make_ok_frame(seq_num: int, messages: list[bytes], dst_port: int = ITCH_UDP_PORT) -> bytes:
    mold = _mold_outer(seq_num, len(messages)) + b"".join(_mold_submsg(m) for m in messages)
    return _eth_ip_udp(dst_port, mold)


def make_nok_count_overflow(seq_num: int, message: bytes, claimed_count: int,
                            dst_port: int = ITCH_UDP_PORT) -> bytes:
    mold = _mold_outer(seq_num, claimed_count) + _mold_submsg(message)
    return _eth_ip_udp(dst_port, mold)


def make_nok_len_overflow(seq_num: int, actual_body: bytes, declared_len: int,
                          dst_port: int = ITCH_UDP_PORT) -> bytes:
    mold = _mold_outer(seq_num, 1) + struct.pack(">H", declared_len) + actual_body
    return _eth_ip_udp(dst_port, mold)


def make_wrong_port_frame(seq_num: int, messages: list[bytes]) -> bytes:
    mold = _mold_outer(seq_num, len(messages)) + b"".join(_mold_submsg(m) for m in messages)
    return _eth_ip_udp(OTHER_UDP_PORT, mold)


def make_tcp_frame() -> bytes:
    tcp_segment = struct.pack(">HH", 12345, OTHER_UDP_PORT) + bytes(22)
    eth = b"\xff\xff\xff\xff\xff\xff\x11\x22\x33\x44\x55\x66\x08\x00"
    return eth + _ip_header(0x06, 20 + len(tcp_segment)) + tcp_segment


def _itch_header(msg_type: int, stock_locate: int = 1, tracking_number: int = 100,
                 timestamp: int = 28_800_000_000_000) -> bytes:
    return (
        bytes([msg_type])
        + stock_locate.to_bytes(2, 'big')
        + tracking_number.to_bytes(2, 'big')
        + timestamp.to_bytes(6, 'big')
    )


def make_system_event(event_code: int, **kw) -> bytes:
    return _itch_header(MSG_SYSTEM_EVENT, **kw) + bytes([event_code])


def make_add_order(order_ref: int, shares: int, stock: bytes, price: int, **kw) -> bytes:
    assert len(stock) == 8
    return (
        _itch_header(MSG_ADD_ORDER, **kw)
        + order_ref.to_bytes(8, 'big')
        + bytes([BUY])
        + shares.to_bytes(4, 'big')
        + stock
        + price.to_bytes(4, 'big')
    )


def make_order_delete(order_ref: int, **kw) -> bytes:
    return _itch_header(MSG_ORDER_DELETE, **kw) + order_ref.to_bytes(8, 'big')


def make_unknown_type_msg() -> bytes:
    return _itch_header(UNKNOWN_TYPE) + bytes([0xAB])


async def reset_dut(dut) -> None:
    dut.rst.value          = 1
    dut.config_valid.value = 0
    dut.cfg_dst_port.value = ITCH_UDP_PORT
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    dut.config_valid.value = 1
    await RisingEdge(dut.clk)
    dut.config_valid.value = 0
    await RisingEdge(dut.clk)


async def wait_for_fields_fresh(dut, max_cycles: int = 600) -> bool:
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        if int(dut.fields_fresh.value) == 1:
            return True
    return False


async def drain(dut, n: int = 120) -> None:
    for _ in range(n):
        await RisingEdge(dut.clk)


@cocotb.test()
async def ok_ok(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg1 = make_system_event(EVENT_START_OF_MESSAGES, stock_locate=1, tracking_number=10, timestamp=1000)
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=1, messages=[msg1]), tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value) == MSG_SYSTEM_EVENT
    assert int(dut.event_code.value)   == EVENT_START_OF_MESSAGES
    assert int(dut.seq_num.value)      == 1

    order_ref = 0x0123456789ABCDEF
    msg2 = make_add_order(order_ref, shares=500, stock=b"AAPL    ", price=1_500_000,
                          stock_locate=2, tracking_number=20, timestamp=2000)
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=2, messages=[msg2]), tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value)           == MSG_ADD_ORDER
    assert int(dut.order_reference_number.value) == order_ref
    assert int(dut.shares.value)                 == 500
    assert int(dut.seq_num.value)                == 2


@cocotb.test()
async def ok_nok_count_overflow(dut):
    """Valid then msg_count overflow: fields_fresh once, then malformed_count increments."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg = make_system_event(EVENT_START_OF_MESSAGES)
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=10, messages=[msg]), tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.malformed_count.value) == 0

    nok = make_nok_count_overflow(seq_num=11, message=msg, claimed_count=3)
    await source.send(AxiStreamFrame(nok, tuser=0))
    await drain(dut, 200)
    assert int(dut.malformed_count.value) == 1


@cocotb.test()
async def nok_count_overflow_ok(dut):
    """msg_count overflow then valid: pipeline recovers and produces fields_fresh."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg = make_system_event(EVENT_START_OF_MESSAGES)
    nok = make_nok_count_overflow(seq_num=1, message=msg, claimed_count=5)
    await source.send(AxiStreamFrame(nok, tuser=0))
    await drain(dut, 200)
    assert int(dut.malformed_count.value) == 1

    order_ref = 0xDEADBEEFCAFEBABE
    ok_msg = make_order_delete(order_ref, stock_locate=5, tracking_number=50, timestamp=5000)
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=2, messages=[ok_msg]), tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value)           == MSG_ORDER_DELETE
    assert int(dut.order_reference_number.value) == order_ref
    assert int(dut.malformed_count.value)        == 1


@cocotb.test()
async def ok_nok_len_overflow(dut):
    """Valid then msg_len overflow: fields_fresh once, then malformed_count increments."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg = make_system_event(EVENT_END_OF_MESSAGES)
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=20, messages=[msg]), tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.malformed_count.value) == 0

    nok = make_nok_len_overflow(seq_num=21, actual_body=b"hello", declared_len=200)
    await source.send(AxiStreamFrame(nok, tuser=0))
    await drain(dut, 200)
    assert int(dut.malformed_count.value) == 1


@cocotb.test()
async def nok_len_overflow_ok(dut):
    """msg_len overflow then valid: pipeline recovers and produces fields_fresh."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    nok = make_nok_len_overflow(seq_num=1, actual_body=bytes(8), declared_len=500)
    await source.send(AxiStreamFrame(nok, tuser=0))
    await drain(dut, 200)
    assert int(dut.malformed_count.value) == 1

    order_ref = 0xCAFEBABE12345678
    ok_msg = make_add_order(order_ref, shares=100, stock=b"MSFT    ", price=3_000_000)
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=2, messages=[ok_msg]), tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value)           == MSG_ADD_ORDER
    assert int(dut.order_reference_number.value) == order_ref
    assert int(dut.malformed_count.value)        == 1


@cocotb.test()
async def ok_nok_ok(dut):
    """valid then count-overflow then valid: two fields_fresh, one malformed increment."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg1 = make_system_event(EVENT_START_OF_MESSAGES, stock_locate=1, tracking_number=1, timestamp=100)
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=1, messages=[msg1]), tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.malformed_count.value) == 0

    nok = make_nok_count_overflow(seq_num=2, message=msg1, claimed_count=10)
    await source.send(AxiStreamFrame(nok, tuser=0))
    await drain(dut, 200)
    assert int(dut.malformed_count.value) == 1

    order_ref = 0x1234_5678_9ABC_DEF0
    msg3 = make_add_order(order_ref, shares=300, stock=b"GOOG    ", price=2_800_000,
                          stock_locate=3, tracking_number=30, timestamp=300)
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=3, messages=[msg3]), tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value)           == MSG_ADD_ORDER
    assert int(dut.order_reference_number.value) == order_ref
    assert int(dut.malformed_count.value)        == 1


@cocotb.test()
async def unknown_itch_type(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg = make_unknown_type_msg()
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=7, messages=[msg]), tuser=0))
    await drain(dut, 200)
    assert int(dut.fields_fresh.value) == 0
    assert int(dut.malformed_count.value) == 1


@cocotb.test()
async def wrong_dst_port_dropped_by_gate(dut):
    """Wrong dst_port: tdest gate discards frame before mold_udp, malformed_count stays 0."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg = make_system_event(EVENT_START_OF_MESSAGES)
    await source.send(AxiStreamFrame(make_wrong_port_frame(seq_num=42, messages=[msg]), tuser=0))
    await drain(dut, 120)
    assert int(dut.malformed_count.value) == 0

    order_ref = 0x1111_2222_3333_4444
    ok_msg = make_order_delete(order_ref)
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=43, messages=[ok_msg]), tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value)           == MSG_ORDER_DELETE
    assert int(dut.order_reference_number.value) == order_ref


@cocotb.test()
async def tcp_frame_dropped_by_gate(dut):
    """TCP frame with non-ITCH dst_port: gate drops it, malformed_count stays 0."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    await source.send(AxiStreamFrame(make_tcp_frame(), tuser=0))
    await drain(dut, 120)
    assert int(dut.malformed_count.value) == 0

    msg = make_system_event(EVENT_START_OF_MESSAGES, stock_locate=9, tracking_number=90, timestamp=9000)
    await source.send(AxiStreamFrame(make_ok_frame(seq_num=99, messages=[msg]), tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value) == MSG_SYSTEM_EVENT


@cocotb.test()
async def multi_message_mold_packet(dut):
    """Two ITCH messages in one MoldUDP64 packet produce two sequential fields_fresh pulses."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg1 = make_system_event(EVENT_START_OF_MESSAGES, stock_locate=1, tracking_number=1, timestamp=100)
    order_ref = 0xABCD_1234_5678_EF01
    msg2 = make_order_delete(order_ref, stock_locate=2, tracking_number=2, timestamp=200)

    await source.send(AxiStreamFrame(make_ok_frame(seq_num=55, messages=[msg1, msg2]), tuser=0))

    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value) == MSG_SYSTEM_EVENT

    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value)           == MSG_ORDER_DELETE
    assert int(dut.order_reference_number.value) == order_ref
