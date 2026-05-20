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
    msg_count = struct.unpack_from(">H", payload, 18)[0]
    await source.send(AxiStreamFrame(payload, tuser=0))
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
async def single_message_fits_in_carry(dut):
    """1-byte message: entire payload in the carry bytes (msg_len=1 < LEN_OVERLAP=2)."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"X"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=1, messages=messages)
    frames = await route_one(source, sink, payload)

    assert len(frames) == 1
    assert bytes(frames[0].tdata) == b"X"


@cocotb.test()
async def single_message_exactly_carry_size(dut):
    """2-byte message: entire payload is the carry bytes (msg_len == LEN_OVERLAP)."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"AB"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=1, messages=messages)
    frames = await route_one(source, sink, payload)

    assert len(frames) == 1
    assert bytes(frames[0].tdata) == b"AB"


@cocotb.test()
async def single_message_carry_plus_one_beat(dut):
    """6-byte message: 2 carry bytes + 1 full 4-byte beat."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"ABCDEF"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=1, messages=messages)
    frames = await route_one(source, sink, payload)

    assert len(frames) == 1
    assert bytes(frames[0].tdata) == b"ABCDEF"


@cocotb.test()
async def single_message_multi_beat(dut):
    """16-byte message: carry + 3 full beats + 2-byte partial last beat."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"0123456789ABCDEF"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=5, messages=messages)
    frames = await route_one(source, sink, payload)

    assert len(frames) == 1
    assert bytes(frames[0].tdata) == b"0123456789ABCDEF"


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
    """Three messages where the second starts mid-beat after the first ends."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"AA", b"BBBBBBBB", b"C"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=7, messages=messages)
    frames = await route_one(source, sink, payload)

    assert len(frames) == 3
    assert bytes(frames[0].tdata) == b"AA"
    assert bytes(frames[1].tdata) == b"BBBBBBBB"
    assert bytes(frames[2].tdata) == b"C"


@cocotb.test()
async def fields_are_captured(dut):
    """Outer header fields are available after parsing."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"data"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=123, messages=messages)
    await source.send(AxiStreamFrame(payload, tuser=0))
    await sink.recv()

    assert int(dut.msg_count.value) == 1
    assert int(dut.seq_num.value) == 123
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
    for _ in range(20):
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
    """Two MoldUDP datagrams back-to-back with the second seq_num captured."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    for seq, msg_data in [(1, b"first_msg"), (2, b"second_message")]:
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
