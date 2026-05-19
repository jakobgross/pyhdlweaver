from ipaddress import IPv4Address

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

from examples.eth_ip.eth_ip import (
    IP_BROADCAST,
    IP_PAYLOAD_OFFSET,
    IP_PROTO_TCP,
    IP_PROTO_UDP,
)

CLOCK_PERIOD_NS = 10
DATA_WIDTH_BYTES = 4

TDEST_BROADCAST = 0
TDEST_UDP = 1
TDEST_OTHER = 3


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
    from scapy.layers.inet import IP, TCP, UDP
    from scapy.layers.l2 import Ether
    from scapy.packet import Raw

    return Ether, IP, Raw, TCP, UDP, scapy_raw


Ether, IP, Raw, TCP, UDP, raw = _import_scapy_offline()


async def reset_dut(dut) -> None:
    dut.rst.value = 1

    for _ in range(4):
        await RisingEdge(dut.clk)

    dut.rst.value = 0
    await RisingEdge(dut.clk)


def forwarded_offset() -> int:
    # First byte after the final parse beat boundary (beats are DATA_WIDTH_BYTES wide).
    parse_beat_count = (IP_PAYLOAD_OFFSET + DATA_WIDTH_BYTES - 1) // DATA_WIDTH_BYTES
    return parse_beat_count * DATA_WIDTH_BYTES


async def send_frame(dut, frame_bytes: bytes) -> AxiStreamFrame:
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)

    await reset_dut(dut)
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))

    return await sink.recv()


def make_frame(dst_ip: str, proto: str = "udp") -> bytes:
    transport = UDP(sport=1234, dport=5678) if proto == "udp" else TCP(sport=1234, dport=5678)
    packet = (
        Ether(dst="ff:ff:ff:ff:ff:ff", src="00:11:22:33:44:55")
        / IP(src="10.0.0.1", dst=dst_ip, flags="DF", id=0x1234)
        / transport
        / Raw(load=b"pyhdlweaver")
    )
    return raw(packet)


async def route_one(source, sink, frame_bytes: bytes) -> AxiStreamFrame:
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    return await sink.recv()


@cocotb.test()
async def routes_unicast_udp_to_tdest_1(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes = make_frame(dst_ip="192.168.1.20", proto="udp")
    frame = await send_frame(dut, frame_bytes)

    assert bytes(frame.tdata) == frame_bytes[forwarded_offset():]
    assert int(frame.tdest) == TDEST_UDP
    assert int(frame.tuser) == 0
    assert int(dut.ip_protocol_reg.value) == IP_PROTO_UDP
    assert int(dut.ip_dst_reg.value) == int(IPv4Address("192.168.1.20"))


@cocotb.test()
async def routes_unicast_tcp_to_tdest_3(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes = make_frame(dst_ip="10.0.0.2", proto="tcp")
    frame = await send_frame(dut, frame_bytes)

    assert bytes(frame.tdata) == frame_bytes[forwarded_offset():]
    assert int(frame.tdest) == TDEST_OTHER
    assert int(frame.tuser) == 0
    assert int(dut.ip_protocol_reg.value) == IP_PROTO_TCP
    assert int(dut.ip_dst_reg.value) == int(IPv4Address("10.0.0.2"))


@cocotb.test()
async def routes_broadcast_tcp_to_tdest_0(dut):
    # ip_dst lands on the final parse beat (beat 8, bytes 32-35 on a 32-bit bus).
    # Without the _comb bypass, ip_dst_reg would still hold 0 when the route decision
    # is made and this test would fail (tdest would be TDEST_OTHER instead of 0).
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes = make_frame(dst_ip="255.255.255.255", proto="tcp")
    frame = await send_frame(dut, frame_bytes)

    assert bytes(frame.tdata) == frame_bytes[forwarded_offset():]
    assert int(frame.tdest) == TDEST_BROADCAST
    assert int(frame.tuser) == 0
    assert int(dut.ip_dst_reg.value) == IP_BROADCAST


@cocotb.test()
async def routes_broadcast_udp_to_tdest_0(dut):
    # Broadcast overrides the UDP match because ip_dst is evaluated last in the
    # always_comb priority chain (last-wins), so tdest = 0 even though protocol is UDP.
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes = make_frame(dst_ip="255.255.255.255", proto="udp")
    frame = await send_frame(dut, frame_bytes)

    assert bytes(frame.tdata) == frame_bytes[forwarded_offset():]
    assert int(frame.tdest) == TDEST_BROADCAST
    assert int(frame.tuser) == 0
    assert int(dut.ip_dst_reg.value) == IP_BROADCAST
    assert int(dut.ip_protocol_reg.value) == IP_PROTO_UDP


@cocotb.test()
async def udp_then_tcp(dut):
    """Route a unicast UDP frame to tdest 1, then a unicast TCP frame to tdest 3."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    udp_bytes = make_frame(dst_ip="10.0.0.1", proto="udp")
    tcp_bytes = make_frame(dst_ip="10.0.0.1", proto="tcp")

    frame = await route_one(source, sink, udp_bytes)
    assert int(frame.tdest) == TDEST_UDP

    frame = await route_one(source, sink, tcp_bytes)
    assert int(frame.tdest) == TDEST_OTHER


@cocotb.test()
async def tcp_then_udp(dut):
    """Route a unicast TCP frame to tdest 3, then a unicast UDP frame to tdest 1."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    udp_bytes = make_frame(dst_ip="10.0.0.1", proto="udp")
    tcp_bytes = make_frame(dst_ip="10.0.0.1", proto="tcp")

    frame = await route_one(source, sink, tcp_bytes)
    assert int(frame.tdest) == TDEST_OTHER

    frame = await route_one(source, sink, udp_bytes)
    assert int(frame.tdest) == TDEST_UDP


@cocotb.test()
async def two_udp_frames(dut):
    """Route two consecutive unicast UDP frames to tdest 1."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    udp_bytes = make_frame(dst_ip="10.0.0.1", proto="udp")

    for _ in range(2):
        frame = await route_one(source, sink, udp_bytes)
        assert bytes(frame.tdata) == udp_bytes[forwarded_offset():]
        assert int(frame.tdest) == TDEST_UDP


@cocotb.test()
async def udp_tcp_udp(dut):
    """Route UDP to tdest 1, TCP to tdest 3, then UDP to tdest 1 again."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    udp_bytes = make_frame(dst_ip="10.0.0.1", proto="udp")
    tcp_bytes = make_frame(dst_ip="10.0.0.1", proto="tcp")

    frame = await route_one(source, sink, udp_bytes)
    assert bytes(frame.tdata) == udp_bytes[forwarded_offset():]
    assert int(frame.tdest) == TDEST_UDP

    frame = await route_one(source, sink, tcp_bytes)
    assert int(frame.tdest) == TDEST_OTHER

    frame = await route_one(source, sink, udp_bytes)
    assert bytes(frame.tdata) == udp_bytes[forwarded_offset():]
    assert int(frame.tdest) == TDEST_UDP
