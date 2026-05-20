"""Cocotb tests for itch_parser_8bit (reused for 32/64-bit via Makefile)."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSource

CLOCK_PERIOD_NS = 10

MSG_SYSTEM_EVENT = 0x53   # 'S'
MSG_ADD_ORDER    = 0x41   # 'A'
MSG_ORDER_DELETE = 0x44   # 'D'
MSG_NOII         = 0x49   # 'I'

EVENT_START_OF_MESSAGES = ord('O')
EVENT_END_OF_MESSAGES   = ord('C')
EVENT_START_SYS_HOURS   = ord('S')

BUY  = ord('B')
SELL = ord('S')


def make_header(msg_type, stock_locate=1, tracking_number=100, timestamp=28_800_000_000_000):
    return (
        bytes([msg_type])
        + stock_locate.to_bytes(2, 'big')
        + tracking_number.to_bytes(2, 'big')
        + timestamp.to_bytes(6, 'big')
    )


def make_system_event(event_code, **kw):
    return make_header(MSG_SYSTEM_EVENT, **kw) + bytes([event_code])


def make_order_delete(order_ref_num, **kw):
    return make_header(MSG_ORDER_DELETE, **kw) + order_ref_num.to_bytes(8, 'big')


def make_add_order(order_ref_num, buy_sell, shares, stock, price, **kw):
    assert len(stock) == 8
    return (
        make_header(MSG_ADD_ORDER, **kw)
        + order_ref_num.to_bytes(8, 'big')
        + bytes([buy_sell])
        + shares.to_bytes(4, 'big')
        + stock
        + price.to_bytes(4, 'big')
    )


def make_noii(paired, imbalance, direction, stock, far, near, ref, cross_type, price_var, **kw):
    assert len(stock) == 8
    return (
        make_header(MSG_NOII, **kw)
        + paired.to_bytes(8, 'big')
        + imbalance.to_bytes(8, 'big')
        + bytes([direction])
        + stock
        + far.to_bytes(4, 'big')
        + near.to_bytes(4, 'big')
        + ref.to_bytes(4, 'big')
        + bytes([cross_type])
        + bytes([price_var])
    )


async def reset_dut(dut):
    dut.rst.value = 1
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def wait_for_fields_fresh(dut, max_cycles=300):
    # RisingEdge wakes in the VPI active region; the value read here is post-NBA
    # from the previous edge, so all field registers from the last beat are settled.
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        if int(dut.fields_fresh.value) == 1:
            return True
    return False


@cocotb.test()
async def fields_valid_low_on_reset(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    await reset_dut(dut)
    assert int(dut.fields_valid.value) == 0
    assert int(dut.fields_fresh.value) == 0


@cocotb.test()
async def parses_system_event_message(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    stock_locate    = 42
    tracking_number = 100
    timestamp       = 28_800_000_000_000
    event_code      = EVENT_START_SYS_HOURS

    msg = make_system_event(
        event_code,
        stock_locate=stock_locate,
        tracking_number=tracking_number,
        timestamp=timestamp,
    )
    assert len(msg) == 12

    await source.send(AxiStreamFrame(msg, tuser=0))
    assert await wait_for_fields_fresh(dut)

    assert int(dut.message_type.value)    == MSG_SYSTEM_EVENT
    assert int(dut.stock_locate.value)    == stock_locate
    assert int(dut.tracking_number.value) == tracking_number
    assert int(dut.timestamp.value)       == timestamp
    assert int(dut.event_code.value)      == event_code
    assert int(dut.fields_valid.value)    == 1


@cocotb.test()
async def parses_order_delete_message(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    order_ref = 0xDEADBEEFCAFEBABE
    msg = make_order_delete(order_ref)
    assert len(msg) == 19

    await source.send(AxiStreamFrame(msg, tuser=0))
    assert await wait_for_fields_fresh(dut)

    assert int(dut.message_type.value)           == MSG_ORDER_DELETE
    assert int(dut.order_reference_number.value) == order_ref


@cocotb.test()
async def parses_add_order_message(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    order_ref = 0x0123456789ABCDEF
    shares    = 1000
    price     = 1_500_000   # $150.0000 with 4 implied decimal places
    stock     = b"PYHDL   "

    msg = make_add_order(
        order_ref_num=order_ref,
        buy_sell=BUY,
        shares=shares,
        stock=stock,
        price=price,
    )
    assert len(msg) == 36

    await source.send(AxiStreamFrame(msg, tuser=0))
    assert await wait_for_fields_fresh(dut)

    assert int(dut.message_type.value)           == MSG_ADD_ORDER
    assert int(dut.order_reference_number.value) == order_ref
    assert int(dut.buy_sell_indicator.value)     == BUY
    assert int(dut.shares.value)                 == shares
    assert int(dut.order_stock.value)            == int.from_bytes(stock, 'big')
    assert int(dut.price.value)                  == price


@cocotb.test()
async def parses_noii_message(dut):
    """NOII is 50 bytes, exercising the full FSM depth."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    paired    = 500_000
    imbalance = 100_000
    far       = 1_500_000
    near      = 1_499_000
    ref       = 1_498_000
    stock     = b"AAPL    "

    msg = make_noii(
        paired=paired,
        imbalance=imbalance,
        direction=ord('B'),
        stock=stock,
        far=far,
        near=near,
        ref=ref,
        cross_type=ord('C'),
        price_var=ord('1'),
    )
    assert len(msg) == 50

    await source.send(AxiStreamFrame(msg, tuser=0))
    assert await wait_for_fields_fresh(dut)

    assert int(dut.message_type.value)              == MSG_NOII
    assert int(dut.paired_shares.value)             == paired
    assert int(dut.imbalance_shares.value)          == imbalance
    assert int(dut.imbalance_direction.value)       == ord('B')
    assert int(dut.noii_stock.value)                == int.from_bytes(stock, 'big')
    assert int(dut.far_price.value)                 == far
    assert int(dut.near_price.value)                == near
    assert int(dut.current_reference_price.value)   == ref
    assert int(dut.noii_cross_type.value)           == ord('C')
    assert int(dut.price_variation_indicator.value) == ord('1')


@cocotb.test()
async def fields_fresh_pulses_for_one_cycle(dut):
    """fields_fresh is high for exactly one clock cycle after each complete message."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg = make_system_event(EVENT_START_OF_MESSAGES)
    await source.send(AxiStreamFrame(msg, tuser=0))
    assert await wait_for_fields_fresh(dut)

    await RisingEdge(dut.clk)
    assert int(dut.fields_fresh.value) == 0


@cocotb.test()
async def two_consecutive_messages_different_types(dut):
    """fields_fresh pulses independently for each message."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    msg1 = make_system_event(EVENT_END_OF_MESSAGES, stock_locate=1, tracking_number=10, timestamp=1000)
    await source.send(AxiStreamFrame(msg1, tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value) == MSG_SYSTEM_EVENT
    assert int(dut.event_code.value)   == EVENT_END_OF_MESSAGES

    order_ref = 0xABCDEF0123456789
    msg2 = make_order_delete(order_ref, stock_locate=2, tracking_number=20, timestamp=2000)
    await source.send(AxiStreamFrame(msg2, tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.message_type.value)           == MSG_ORDER_DELETE
    assert int(dut.order_reference_number.value) == order_ref
    assert int(dut.fields_valid.value)           == 1


@cocotb.test()
async def over_long_frame_drains_then_recovers(dut):
    """A frame longer than PARSE_BEATS enters ST_DRAIN without asserting fields_fresh."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    # 51-byte frame triggers ST_DRAIN since PARSE_BEATS=50
    oversized = make_system_event(EVENT_START_OF_MESSAGES) + bytes(39)
    assert len(oversized) == 51

    await source.send(AxiStreamFrame(oversized, tuser=0))
    fresh_seen = False
    for _ in range(120):
        await RisingEdge(dut.clk)
        if int(dut.fields_fresh.value) == 1:
            fresh_seen = True
            break
    assert not fresh_seen, "fields_fresh must not pulse for an over-long (drained) frame"

    order_ref = 0x1234567890ABCDEF
    msg = make_order_delete(order_ref)
    await source.send(AxiStreamFrame(msg, tuser=0))
    assert await wait_for_fields_fresh(dut), "parser did not recover after drain"
    assert int(dut.message_type.value)           == MSG_ORDER_DELETE
    assert int(dut.order_reference_number.value) == order_ref


@cocotb.test()
async def variant_fields_isolated_by_discriminator(dut):
    """Sending an 'A' Add Order must not overwrite event_code captured by the prior 'S' message."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    event_code = EVENT_START_OF_MESSAGES
    msg_s = make_system_event(event_code)
    await source.send(AxiStreamFrame(msg_s, tuser=0))
    assert await wait_for_fields_fresh(dut)
    assert int(dut.event_code.value) == event_code

    # 'A' uses offset 11 for order_reference_number, not event_code.
    order_ref = 0xCAFEBABEDEADBEEF
    msg_a = make_add_order(
        order_ref_num=order_ref,
        buy_sell=BUY,
        shares=500,
        stock=b"AAPL    ",
        price=1_900_000,
    )
    await source.send(AxiStreamFrame(msg_a, tuser=0))
    assert await wait_for_fields_fresh(dut)

    assert int(dut.message_type.value)           == MSG_ADD_ORDER
    assert int(dut.order_reference_number.value) == order_ref
    # event_code_reg was NOT written by the 'A' variant; stale value from 'S' persists.
    assert int(dut.event_code.value) == event_code
