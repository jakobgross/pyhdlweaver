from ipaddress import IPv4Address

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

from examples.eth_ip.eth_ip import IP_PAYLOAD_OFFSET

CLOCK_PERIOD_NS = 10
DATA_WIDTH_BYTES = 3


def _import_scapy_offline():
    import scapy.interfaces

    scapy.interfaces.NetworkInterfaceDict.reload = lambda self: None
    scapy.interfaces.NetworkInterfaceDict.load_confiface = lambda self: None

    import scapy.arch

    scapy.arch.read_routes = lambda: []
    scapy.arch.read_routes6 = lambda: []
    scapy.arch.get_if_raw_addr = lambda iff: b"\x00\x00\x00\x00"
    scapy.arch.in6_getifaddr = lambda: []

    from scapy.compat import raw as scapy_raw
    from scapy.layers.inet import IP, UDP
    from scapy.layers.l2 import Ether
    from scapy.packet import Raw

    return Ether, IP, Raw, UDP, scapy_raw


Ether, IP, Raw, UDP, raw = _import_scapy_offline()


async def reset_dut(dut) -> None:
    dut.rst.value = 1
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


def forwarded_offset() -> int:
    return IP_PAYLOAD_OFFSET


async def send_one(source, sink, frame_bytes: bytes, tuser=0) -> AxiStreamFrame:
    await source.send(AxiStreamFrame(frame_bytes, tuser=tuser))
    return await sink.recv()


def assert_forwarded_frame(frame: AxiStreamFrame, frame_bytes: bytes) -> None:
    assert bytes(frame.tdata) == frame_bytes[forwarded_offset():]
    assert int(frame.tdest) == 0


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


@cocotb.test()
async def captures_fields_across_24bit_lanes(dut):
    """Field extraction remains byte-correct when header bytes cross 3-byte beats."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame_bytes, packet = udp_frame()
    frame = await send_one(source, sink, frame_bytes)

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
async def two_24bit_frames_back_to_back(dut):
    """The parser resets cleanly between consecutive 24-bit frames."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frames = [udp_frame()[0], non_ipv4_frame()[0], udp_frame()[0]]
    for frame_bytes in frames:
        frame = await send_one(source, sink, frame_bytes)
        assert_forwarded_frame(frame, frame_bytes)
        assert int(frame.tuser) == 0
