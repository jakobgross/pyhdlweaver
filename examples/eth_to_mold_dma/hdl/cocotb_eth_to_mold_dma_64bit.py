"""Cocotb tests for eth_to_mold_dma_64bit."""
import struct

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

CLOCK_PERIOD_NS = 10
SESSION_ID = b"SESSIONID_"
DEFAULT_PORT = 4789


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
    mold = SESSION_ID + struct.pack(">QH", seq_num, len(messages))
    for msg in messages:
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


async def configure_port(dut, port: int) -> None:
    dut.cfg_expected_dst_port.value = port
    dut.config_valid.value = 1
    await RisingEdge(dut.clk)
    dut.config_valid.value = 0
    await RisingEdge(dut.clk)


async def make_streams(dut) -> tuple[AxiStreamSource, AxiStreamSink]:
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)
    return source, sink


async def assert_no_output(dut, source: AxiStreamSource, sink: AxiStreamSink, cycles: int) -> None:
    for _ in range(cycles):
        await RisingEdge(dut.clk)
    assert source.idle()
    assert sink.empty()


@cocotb.test()
async def forwards_each_mold_message_as_one_axi_frame(dut):
    """A MoldUDP packet with two messages produces two output frames."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source, sink = await make_streams(dut)

    messages = [b"ITCH_ONE", b"ITCH_TWO_LONGER"]
    frame = make_frame(messages, seq_num=42)
    cocotb.start_soon(source.send(AxiStreamFrame(frame, tuser=0)))

    first = await sink.recv()
    second = await sink.recv()

    assert bytes(first.tdata) == messages[0]
    assert bytes(second.tdata) == messages[1]
    assert int(first.tuser) == 0
    assert int(second.tuser) == 0
    assert int(dut.mold_seq_num.value) == 42
    assert int(dut.mold_msg_count.value) == 2
    assert int(dut.mold_message_msg_len.value) == len(messages[1])


@cocotb.test()
async def wrong_port_is_dropped_by_default_register(dut):
    """The default registered port is 4789."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source, sink = await make_streams(dut)

    frame = make_frame([b"ITCH"], dst_port=9999)
    await source.send(AxiStreamFrame(frame, tuser=0))
    await assert_no_output(dut, source, sink, len(frame) + 16)

    assert int(dut.wrong_port_drop_count.value) == 1
    assert int(dut.udp_dst_port.value) == 9999


@cocotb.test()
async def configured_port_is_forwarded(dut):
    """A config write updates the accepted UDP destination port."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source, sink = await make_streams(dut)

    await configure_port(dut, 9999)
    frame = make_frame([b"ITCH"], dst_port=9999)
    await source.send(AxiStreamFrame(frame, tuser=0))
    out = await sink.recv()

    assert bytes(out.tdata) == b"ITCH"
    assert int(dut.wrong_port_drop_count.value) == 0


@cocotb.test()
async def non_udp_frame_is_dropped(dut):
    """Only UDP is accepted."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source, sink = await make_streams(dut)

    frame = make_frame([b"ITCH"], ip_proto=0x06)
    await source.send(AxiStreamFrame(frame, tuser=0))
    await assert_no_output(dut, source, sink, len(frame) + 16)

    assert int(dut.non_udp_drop_count.value) == 1


@cocotb.test()
async def non_ipv4_frame_is_dropped(dut):
    """Only IPv4 is accepted."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source, sink = await make_streams(dut)

    frame = make_frame([b"ITCH"], ethertype=0x86DD)
    await source.send(AxiStreamFrame(frame, tuser=0))
    await assert_no_output(dut, source, sink, len(frame) + 16)

    assert int(dut.non_ipv4_drop_count.value) == 1
