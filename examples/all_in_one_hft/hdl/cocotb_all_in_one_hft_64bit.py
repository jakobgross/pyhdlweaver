"""Cocotb tests for all_in_one_hft_parser_64bit."""
import math
import struct

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSource

CLOCK_PERIOD_NS = 10
SESSION_ID = b"SESSIONID_"
DEFAULT_PORT = 4789

MSG_SYSTEM_EVENT = ord("S")  # 12 bytes
MSG_ADD_ORDER = ord("A")     # 36 bytes
MSG_ORDER_DELETE = ord("D")  # 19 bytes

BUY  = ord("B")
SELL = ord("S")


def make_common_header(msg_type, stock_locate=1, tracking_number=100, timestamp=0):
    return (
        bytes([msg_type])
        + stock_locate.to_bytes(2, "big")
        + tracking_number.to_bytes(2, "big")
        + timestamp.to_bytes(6, "big")
    )


def make_system_event(event_code=ord("O"), **kw):
    return make_common_header(MSG_SYSTEM_EVENT, **kw) + bytes([event_code])


def make_add_order(order_ref, buy_sell, shares, stock, price, **kw):
    assert len(stock) == 8
    return (
        make_common_header(MSG_ADD_ORDER, **kw)
        + order_ref.to_bytes(8, "big")
        + bytes([buy_sell])
        + shares.to_bytes(4, "big")
        + stock
        + price.to_bytes(4, "big")
    )


def make_order_delete(order_ref, **kw):
    return make_common_header(MSG_ORDER_DELETE, **kw) + order_ref.to_bytes(8, "big")


def _ip_header(ip_proto, udp_len):
    total_len = 20 + udp_len
    return struct.pack(
        ">BBHHHBBHII",
        0x45, 0x00, total_len, 0, 0, 64, ip_proto, 0,
        0xC0A80102, 0xC0A80101,
    )


def make_frame(itch_messages, dst_port=DEFAULT_PORT, ethertype=0x0800, ip_proto=0x11, seq_num=1):
    mold = SESSION_ID + struct.pack(">QH", seq_num, len(itch_messages))
    for msg in itch_messages:
        mold += struct.pack(">H", len(msg)) + msg
    udp_len = 8 + len(mold)
    udp = struct.pack(">HHHH", 12345, dst_port, udp_len, 0) + mold
    eth = b"\xff\xff\xff\xff\xff\xff\xaa\xbb\xcc\xdd\xee\xff" + struct.pack(">H", ethertype)
    return eth + _ip_header(ip_proto, len(udp)) + udp


async def reset_dut(dut) -> None:
    dut.rst.value = 1
    dut.config_valid.value = 0
    dut.cfg_expected_dst_port.value = 0
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def wait_for_fresh(dut) -> None:
    while not dut.itch_fields_fresh.value:
        await RisingEdge(dut.clk)


@cocotb.test()
async def outer_header_fields_are_parsed(dut):
    """All outer ETH/IP/UDP/MoldUDP header fields are captured correctly."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg = make_system_event(stock_locate=7, tracking_number=99, timestamp=0x123456789ABC)
    frame = make_frame([msg], seq_num=42)
    cocotb.start_soon(source.send(AxiStreamFrame(frame, tuser=0)))
    await wait_for_fresh(dut)

    assert int(dut.eth_ethertype.value) == 0x0800
    assert int(dut.ip_protocol.value) == 0x11
    assert int(dut.udp_dst_port.value) == DEFAULT_PORT
    assert int(dut.mold_session_id.value).to_bytes(10, "big") == SESSION_ID
    assert int(dut.mold_seq_num.value) == 42
    assert int(dut.mold_msg_count.value) == 1


@cocotb.test()
async def itch_fields_are_parsed(dut):
    """ITCH common and variant fields are captured from a System Event message."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg = make_system_event(stock_locate=7, tracking_number=99, timestamp=0x123456789ABC, event_code=ord("O"))
    cocotb.start_soon(source.send(AxiStreamFrame(make_frame([msg]), tuser=0)))
    await wait_for_fresh(dut)

    assert int(dut.message_type.value) == MSG_SYSTEM_EVENT
    assert int(dut.stock_locate.value) == 7
    assert int(dut.tracking_number.value) == 99
    assert int(dut.timestamp.value) == 0x123456789ABC
    assert int(dut.event_code.value) == ord("O")


@cocotb.test()
async def add_order_fields_are_parsed(dut):
    """Add Order variant fields are captured correctly."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg = make_add_order(order_ref=0xDEADBEEF, buy_sell=BUY, shares=100, stock=b"AAPL    ", price=1500_0000)
    cocotb.start_soon(source.send(AxiStreamFrame(make_frame([msg]), tuser=0)))
    await wait_for_fresh(dut)

    assert int(dut.message_type.value) == MSG_ADD_ORDER
    assert int(dut.order_reference_number.value) == 0xDEADBEEF
    assert int(dut.buy_sell_indicator.value) == BUY
    assert int(dut.shares.value) == 100
    assert int(dut.price.value) == 1500_0000


@cocotb.test()
async def two_messages_in_one_frame(dut):
    """Two ITCH messages in one MoldUDP frame each produce a fresh pulse."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msgs = [
        make_system_event(event_code=ord("O"), stock_locate=1),
        make_system_event(event_code=ord("C"), stock_locate=2),
    ]
    cocotb.start_soon(source.send(AxiStreamFrame(make_frame(msgs, seq_num=10), tuser=0)))

    await wait_for_fresh(dut)
    assert int(dut.event_code.value) == ord("O")
    assert int(dut.stock_locate.value) == 1

    await RisingEdge(dut.clk)
    await wait_for_fresh(dut)
    assert int(dut.event_code.value) == ord("C")
    assert int(dut.stock_locate.value) == 2


@cocotb.test()
async def non_ipv4_frame_is_dropped(dut):
    """Non-IPv4 ethertype increments non_ipv4_drop_count and yields no fields."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame = make_frame([make_system_event()], ethertype=0x86DD)
    await source.send(AxiStreamFrame(frame, tuser=0))
    for _ in range(50):
        await RisingEdge(dut.clk)

    assert int(dut.non_ipv4_drop_count.value) == 1
    assert int(dut.itch_fields_valid.value) == 0


@cocotb.test()
async def wrong_port_is_dropped(dut):
    """Wrong UDP destination port increments wrong_port_drop_count."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame = make_frame([make_system_event()], dst_port=9999)
    await source.send(AxiStreamFrame(frame, tuser=0))
    for _ in range(50):
        await RisingEdge(dut.clk)

    assert int(dut.wrong_port_drop_count.value) == 1
    assert int(dut.itch_fields_valid.value) == 0


@cocotb.test()
async def consecutive_frames(dut):
    """Back-to-back frames each parse correctly."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    for seq_num in [1, 2, 3]:
        msg = make_system_event(stock_locate=seq_num, event_code=ord("O"))
        frame = make_frame([msg], seq_num=seq_num)
        cocotb.start_soon(source.send(AxiStreamFrame(frame, tuser=0)))
        await wait_for_fresh(dut)
        assert int(dut.mold_seq_num.value) == seq_num
        assert int(dut.stock_locate.value) == seq_num
        await RisingEdge(dut.clk)


@cocotb.test()
async def throughput_no_stall_per_beat(dut):
    """On a 64-bit bus, total cycles from first beat to fresh equals bytes/8 beats + scratch drain."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    # System Event: 62 outer + 2 msg_len + 12 ITCH = 76 bytes total.
    # 64-bit bus: 8 outer beats + 2 MSG_HDR scratch-drain + 12 MSG_BODY bytes = 22 cycles.
    msg = make_system_event()
    frame = make_frame([msg])
    bus_width = 8
    # Outer beats: ceil(62/8) = 8.  Tail preloads 2 msg_len bytes into scratch.
    # MSG_HDR: 2 drain cycles (no new beats).
    # MSG_BODY: 12 bytes, 1 byte/cycle = 12 cycles.
    outer_beats = math.ceil(62 / bus_width)
    sub_header_bytes = 2
    itch_bytes = 12
    # Optimal: 8 outer beats + 2 MSG_HDR drain + 12 MSG_BODY bytes = 22 cycles.
    # +1 for the AXI source driver's 1-cycle startup latency before first tvalid.
    expected_cycles = outer_beats + sub_header_bytes + itch_bytes + 1  # 23

    cycle_count = 0
    cocotb.start_soon(source.send(AxiStreamFrame(frame, tuser=0)))

    # Wait for first handshake, then start counting.
    while not (dut.s_axis_tvalid.value and dut.s_axis_tready.value):
        await RisingEdge(dut.clk)
    cycle_count = 1

    while not dut.itch_fields_fresh.value:
        await RisingEdge(dut.clk)
        cycle_count += 1

    assert cycle_count == expected_cycles, (
        f"Expected {expected_cycles} cycles, got {cycle_count}"
    )
