import struct

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

from examples.mold_udp.mold_udp import make_mold_udp_payload

CLOCK_PERIOD_NS = 10
SESSION_ID = b"SESSIONID_"


async def reset_dut(dut) -> None:
    dut.rst.value = 1
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def route_one(source, sink, payload: bytes) -> list[AxiStreamFrame]:
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
async def multiple_messages_varied_lengths(dut):
    """Several messages with boundaries that do not align to 24-bit or 512-bit lanes."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    messages = [b"A", b"BCDE", b"0123456789abcdef", b"Z"]
    payload = make_mold_udp_payload(SESSION_ID, seq_num=100, messages=messages)
    frames = await route_one(source, sink, payload)

    assert len(frames) == len(messages)
    for frame, expected in zip(frames, messages):
        assert bytes(frame.tdata) == expected
        assert int(frame.tuser) == 0

    assert int(dut.msg_count.value) == len(messages)
    assert int(dut.seq_num.value) == 100
    assert int(dut.malformed_count.value) == 0


@cocotb.test()
async def zero_length_message_is_malformed(dut):
    """A zero-length sub-message increments the error counter and recovers."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    payload = make_zero_length_payload(seq_num=155, trailer=b"junk")
    await source.send(AxiStreamFrame(payload, tuser=0))
    for _ in range(80):
        await RisingEdge(dut.clk)

    assert int(dut.malformed_count.value) == 1

    valid_payload = make_mold_udp_payload(SESSION_ID, seq_num=157, messages=[b"ok"])
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

    payload = make_truncated_payload(seq_num=156, declared_len=8, payload=b"abc")
    await source.send(AxiStreamFrame(payload, tuser=0))
    frame = await sink.recv()
    await RisingEdge(dut.clk)

    assert bytes(frame.tdata) == b"abc"
    assert frame_tuser_values(frame)[-1] == 1
    assert int(dut.malformed_count.value) == 1


@cocotb.test()
async def multiple_datagrams_back_to_back(dut):
    """Multiple MoldUDP frames after each other, each carrying multiple messages."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    datagrams = [
        (201, [b"first", b"second-message"]),
        (202, [b"x", b"yy", b"zzz"]),
        (203, [b"wide-bus-payload", b"tail"]),
    ]

    for seq_num, messages in datagrams:
        payload = make_mold_udp_payload(SESSION_ID, seq_num=seq_num, messages=messages)
        frames = await route_one(source, sink, payload)
        assert len(frames) == len(messages)
        for frame, expected in zip(frames, messages):
            assert bytes(frame.tdata) == expected
            assert int(frame.tuser) == 0
        assert int(dut.seq_num.value) == seq_num
        assert int(dut.msg_count.value) == len(messages)

    assert int(dut.malformed_count.value) == 0
