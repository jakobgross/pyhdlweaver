import struct

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

from examples.mold_udp.mold_udp import make_mold_udp_payload

CLOCK_PERIOD_NS = 10
SESSION_ID = b"SESSIONID_"  # exactly 10 bytes


async def reset_dut(dut) -> None:
    dut.rst.value = 1
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def route_one(source, sink, payload: bytes) -> list[AxiStreamFrame]:
    """Send one MoldUDP payload and collect all output frames."""
    await source.send(AxiStreamFrame(payload, tuser=0))
    # msg_count is the last 2 bytes of the 20-byte outer header
    msg_count = struct.unpack_from(">H", payload, 18)[0]
    frames = []
    for _ in range(msg_count):
        frames.append(await sink.recv())
    return frames


def frame_tuser_values(frame: AxiStreamFrame) -> list[int]:
    if frame.tuser is None:
        return [0] * len(frame.tdata)
    if isinstance(frame.tuser, (bool, int)):
        return [int(frame.tuser)] * len(frame.tdata)
    return [int(value) for value in frame.tuser]


def make_truncated_payload(seq_num: int, declared_len: int, payload: bytes) -> bytes:
    header = SESSION_ID + struct.pack(">QH", seq_num, 1)
    return header + struct.pack(">H", declared_len) + payload


def make_zero_length_payload(seq_num: int, trailer: bytes = b"") -> bytes:
    header = SESSION_ID + struct.pack(">QH", seq_num, 1)
    return header + struct.pack(">H", 0) + trailer


@cocotb.test()
async def single_message_short(dut):
    """Single 3-byte message uses 3 beats on an 8-bit bus."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"abc"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=1, messages=messages)
    frames = await route_one(source, sink, payload)

    assert len(frames) == 1
    assert bytes(frames[0].tdata) == b"abc"
    assert int(frames[0].tuser) == 0


@cocotb.test()
async def single_message_multi_beat(dut):
    """Single 10-byte message spread across multiple 8-bit beats."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"0123456789"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=1, messages=messages)
    frames = await route_one(source, sink, payload)

    assert len(frames) == 1
    assert bytes(frames[0].tdata) == b"0123456789"


@cocotb.test()
async def two_messages(dut):
    """Two messages are output as separate AXI-Stream frames."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"hello", b"world"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=10, messages=messages)
    frames = await route_one(source, sink, payload)

    assert len(frames) == 2
    assert bytes(frames[0].tdata) == b"hello"
    assert bytes(frames[1].tdata) == b"world"


@cocotb.test()
async def three_messages_varied_lengths(dut):
    """Three messages with different lengths."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"A", b"BB", b"CCC"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=42, messages=messages)
    frames = await route_one(source, sink, payload)

    assert len(frames) == 3
    assert bytes(frames[0].tdata) == b"A"
    assert bytes(frames[1].tdata) == b"BB"
    assert bytes(frames[2].tdata) == b"CCC"


@cocotb.test()
async def fields_valid_and_fresh_after_outer_header(dut):
    """fields_valid rises and fields_fresh pulses once after outer header is parsed."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"test"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=99, messages=messages)
    await source.send(AxiStreamFrame(payload, tuser=0))
    await sink.recv()

    assert int(dut.msg_count.value) == 1
    assert int(dut.seq_num.value) == 99
    assert int(dut.mold_message_msg_len.value) == 4


@cocotb.test()
async def zero_length_message_is_malformed(dut):
    """A zero-length sub-message increments the error counter and recovers."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    payload = make_zero_length_payload(seq_num=55, trailer=b"junk")
    await source.send(AxiStreamFrame(payload, tuser=0))
    for _ in range(80):
        await RisingEdge(dut.clk)

    assert int(dut.malformed_count.value) == 1

    valid_payload = make_mold_udp_payload(SESSION_ID, seq_num=57, messages=[b"ok"])
    frames = await route_one(source, sink, valid_payload)

    assert bytes(frames[0].tdata) == b"ok"
    assert int(dut.malformed_count.value) == 1


@cocotb.test()
async def truncated_message_is_malformed(dut):
    """Declared payload length is longer than the remaining input frame."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    payload = make_truncated_payload(seq_num=56, declared_len=8, payload=b"abc")
    await source.send(AxiStreamFrame(payload, tuser=0))
    frame = await sink.recv()
    await RisingEdge(dut.clk)

    assert bytes(frame.tdata) == b"abc"
    assert frame_tuser_values(frame)[-1] == 1
    assert int(dut.malformed_count.value) == 1


@cocotb.test()
async def two_consecutive_datagrams(dut):
    """Send two MoldUDP datagrams back-to-back."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    for seq, msg_data in [(1, b"first"), (2, b"second")]:
        payload = make_mold_udp_payload(SESSION_ID, seq_num=seq, messages=[msg_data])
        frames = await route_one(source, sink, payload)
        assert bytes(frames[0].tdata) == msg_data
        assert int(dut.seq_num.value) == seq


@cocotb.test()
async def consecutive_datagrams_with_multiple_messages(dut):
    """Back-to-back datagrams, each with more than one sub-message."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    datagrams = [
        (11, [b"one", b"two"]),
        (12, [b"alpha", b"beta", b"gamma"]),
    ]

    for seq, messages in datagrams:
        payload = make_mold_udp_payload(SESSION_ID, seq_num=seq, messages=messages)
        frames = await route_one(source, sink, payload)
        assert [bytes(frame.tdata) for frame in frames] == messages
        assert int(dut.seq_num.value) == seq
        assert int(dut.msg_count.value) == len(messages)
