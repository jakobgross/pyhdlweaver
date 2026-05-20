from ipaddress import IPv4Address

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

from examples.eth_ip.eth_ip import IP_PAYLOAD_OFFSET

CLOCK_PERIOD_NS = 10
DATA_WIDTH_BYTES = 4


def _import_scapy_offline():
    """Import packet-building Scapy pieces without host network probing."""

    import scapy.interfaces

    scapy.interfaces.NetworkInterfaceDict.reload = lambda self: None
    scapy.interfaces.NetworkInterfaceDict.load_confiface = lambda self: None

    import scapy.arch

    scapy.arch.read_routes = lambda: []
    scapy.arch.read_routes6 = lambda: []
    scapy.arch.get_if_raw_addr = lambda iff: b"\x00\x00\x00\x00"
    scapy.arch.in6_getifaddr = lambda: []

    from scapy.compat import raw as scapy_raw
    from scapy.layers.inet import ICMP, IP, TCP, UDP
    from scapy.layers.l2 import Ether
    from scapy.packet import Raw

    return Ether, ICMP, IP, Raw, TCP, UDP, scapy_raw


Ether, ICMP, IP, Raw, TCP, UDP, raw = _import_scapy_offline()


async def reset_dut(dut) -> None:
    dut.rst.value = 1

    for _ in range(4):
        await RisingEdge(dut.clk)

    dut.rst.value = 0
    await RisingEdge(dut.clk)


def tuser_on_beat(frame_bytes: bytes, beat_index: int) -> list[int]:
    tuser = [0] * len(frame_bytes)
    last_byte = min(len(frame_bytes) - 1, ((beat_index + 1) * DATA_WIDTH_BYTES) - 1)
    tuser[last_byte] = 1
    return tuser


def frame_tuser_values(frame: AxiStreamFrame) -> list[int]:
    if frame.tuser is None:
        return [0] * len(frame.tdata)
    if isinstance(frame.tuser, (bool, int)):
        return [int(frame.tuser)] * len(frame.tdata)
    return [int(value) for value in frame.tuser]


def forwarded_offset() -> int:
    return IP_PAYLOAD_OFFSET


def udp_frame() -> tuple[bytes, Ether]:
    packet = (
        Ether(dst="00:11:22:33:44:55", src="66:77:88:99:aa:bb")
        / IP(src="192.168.1.10", dst="192.168.1.20", flags="DF", id=0x1234)
        / UDP(sport=0x1122, dport=0x3344)
        / Raw(load=b"pyhdlweaver")
    )
    frame_bytes = raw(packet)
    return frame_bytes, Ether(frame_bytes)


def non_ipv4_frame() -> tuple[bytes, Ether]:
    payload = bytes(range(64))
    packet = Ether(dst="00:11:22:33:44:55", src="66:77:88:99:aa:bb", type=0x0806) / Raw(load=payload)
    frame_bytes = raw(packet)
    return frame_bytes, Ether(frame_bytes)


async def send_frame(dut, frame_bytes: bytes, tuser=None) -> AxiStreamFrame:
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)

    await reset_dut(dut)

    await source.send(AxiStreamFrame(frame_bytes, tuser=tuser or 0))
    return await sink.recv()


async def send_one(source, sink, frame_bytes: bytes, tuser=0) -> AxiStreamFrame:
    await source.send(AxiStreamFrame(frame_bytes, tuser=tuser))
    return await sink.recv()


def assert_forwarded_frame(frame: AxiStreamFrame, frame_bytes: bytes) -> None:
    assert bytes(frame.tdata) == frame_bytes[forwarded_offset():]
    assert int(frame.tdest) == 0


@cocotb.test()
async def captures_fields_from_scapy_udp_frame(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes, packet = udp_frame()
    frame = await send_frame(dut, frame_bytes)

    assert_forwarded_frame(frame, frame_bytes)
    assert int(frame.tuser) == 0

    ip = packet[IP]
    expected_version_ihl = (ip.version << 4) | ip.ihl
    expected_flags_frag = (int(ip.flags) << 13) | ip.frag

    assert int(dut.eth_ethertype.value) == packet.type
    assert int(dut.ip_version_ihl.value) == expected_version_ihl
    assert int(dut.ip_total_length.value) == ip.len
    assert int(dut.ip_flags_frag.value) == expected_flags_frag
    assert int(dut.ip_protocol.value) == ip.proto
    assert int(dut.ip_src.value) == int(IPv4Address(ip.src))
    assert int(dut.ip_dst.value) == int(IPv4Address(ip.dst))


@cocotb.test()
async def captures_non_ipv4_ethertype(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes, packet = non_ipv4_frame()
    frame = await send_frame(dut, frame_bytes)

    assert_forwarded_frame(frame, frame_bytes)
    assert int(frame.tuser) == 0
    assert int(dut.eth_ethertype.value) == packet.type


@cocotb.test()
async def propagates_tuser_seen_before_payload_forwarding(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes, _ = udp_frame()
    frame = await send_frame(dut, frame_bytes, tuser=tuser_on_beat(frame_bytes, beat_index=0))

    assert_forwarded_frame(frame, frame_bytes)
    assert all(value == 1 for value in frame_tuser_values(frame))


@cocotb.test()
async def propagates_tuser_seen_after_payload_forwarding_started(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes, _ = udp_frame()
    first_payload_beat = (IP_PAYLOAD_OFFSET + DATA_WIDTH_BYTES - 1) // DATA_WIDTH_BYTES
    frame = await send_frame(
        dut,
        frame_bytes,
        tuser=tuser_on_beat(frame_bytes, beat_index=first_payload_beat + 1),
    )

    assert_forwarded_frame(frame, frame_bytes)
    parse_tail_bytes = (-IP_PAYLOAD_OFFSET) % DATA_WIDTH_BYTES
    clean_prefix = parse_tail_bytes + DATA_WIDTH_BYTES
    assert frame_tuser_values(frame)[:clean_prefix] == [0] * clean_prefix
    assert all(value == 1 for value in frame_tuser_values(frame)[clean_prefix:])


@cocotb.test()
async def clean_then_error_frame(dut):
    """Forward a clean frame (tuser=0 out), then a frame with tuser=1 on a parse beat."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame_bytes, _ = udp_frame()
    error_tuser = tuser_on_beat(frame_bytes, beat_index=0)

    frame = await send_one(source, sink, frame_bytes)
    assert_forwarded_frame(frame, frame_bytes)
    assert int(frame.tuser) == 0

    frame = await send_one(source, sink, frame_bytes, tuser=error_tuser)
    assert_forwarded_frame(frame, frame_bytes)
    assert all(value == 1 for value in frame_tuser_values(frame))


@cocotb.test()
async def error_frame_then_clean(dut):
    """Forward a frame with tuser=1, then verify the next frame has tuser=0 (sticky cleared)."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame_bytes, _ = udp_frame()
    error_tuser = tuser_on_beat(frame_bytes, beat_index=0)

    frame = await send_one(source, sink, frame_bytes, tuser=error_tuser)
    assert all(value == 1 for value in frame_tuser_values(frame))

    frame = await send_one(source, sink, frame_bytes)
    assert_forwarded_frame(frame, frame_bytes)
    assert int(frame.tuser) == 0


@cocotb.test()
async def two_clean_frames(dut):
    """Forward two consecutive clean frames."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame_bytes, _ = udp_frame()
    for _ in range(2):
        frame = await send_one(source, sink, frame_bytes)
        assert_forwarded_frame(frame, frame_bytes)
        assert int(frame.tuser) == 0


@cocotb.test()
async def clean_error_clean(dut):
    """Forward clean, then error, then clean to verify sticky_tuser resets between frames."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame_bytes, _ = udp_frame()
    error_tuser = tuser_on_beat(frame_bytes, beat_index=0)

    frame = await send_one(source, sink, frame_bytes)
    assert int(frame.tuser) == 0

    frame = await send_one(source, sink, frame_bytes, tuser=error_tuser)
    assert all(value == 1 for value in frame_tuser_values(frame))

    frame = await send_one(source, sink, frame_bytes)
    assert_forwarded_frame(frame, frame_bytes)
    assert int(frame.tuser) == 0
