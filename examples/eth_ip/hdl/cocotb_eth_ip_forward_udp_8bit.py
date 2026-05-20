import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

from examples.eth_ip.eth_ip import IP_PAYLOAD_OFFSET, IP_PROTO_TCP, IP_PROTO_UDP

CLOCK_PERIOD_NS = 10
DATA_WIDTH_BYTES = 1


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


def udp_frame() -> tuple[bytes, Ether]:
    packet = (
        Ether(dst="00:11:22:33:44:55", src="66:77:88:99:aa:bb")
        / IP(src="192.168.1.10", dst="192.168.1.20", flags="DF", id=0x1234)
        / UDP(sport=0x1122, dport=0x3344)
        / Raw(load=b"pyhdlweaver")
    )
    frame_bytes = raw(packet)
    return frame_bytes, Ether(frame_bytes)


def tcp_frame() -> tuple[bytes, Ether]:
    packet = (
        Ether(dst="00:11:22:33:44:55", src="66:77:88:99:aa:bb")
        / IP(src="192.168.1.10", dst="192.168.1.20", flags="DF", id=0x1234)
        / TCP(sport=0x1122, dport=0x3344)
        / Raw(load=b"pyhdlweaver")
    )
    frame_bytes = raw(packet)
    return frame_bytes, Ether(frame_bytes)


async def send_frame(dut, frame_bytes: bytes) -> tuple[AxiStreamSink, AxiStreamSource]:
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)

    await reset_dut(dut)
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))

    return sink, source


async def forward_one(source, sink, frame_bytes: bytes) -> AxiStreamFrame:
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    return await sink.recv()


async def drop_one(source, sink, frame_bytes: bytes, dut) -> None:
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    for _ in range(len(frame_bytes) + 8):
        await RisingEdge(dut.clk)
    assert source.idle()
    assert sink.empty()


@cocotb.test()
async def forwards_udp_packet_on_8_bit_axi(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes, packet = udp_frame()
    sink, _ = await send_frame(dut, frame_bytes)
    frame = await sink.recv()

    assert bytes(frame.tdata) == frame_bytes[IP_PAYLOAD_OFFSET:]
    assert int(frame.tdest) == 0
    assert int(frame.tuser) == 0
    assert int(dut.ip_protocol.value) == packet[IP].proto
    assert packet[IP].proto == IP_PROTO_UDP
    assert int(dut.non_udp_drop_count.value) == 0


@cocotb.test()
async def drops_tcp_packet_on_8_bit_axi(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes, packet = tcp_frame()
    sink, source = await send_frame(dut, frame_bytes)

    for _ in range(len(frame_bytes) + 8):
        await RisingEdge(dut.clk)

    assert source.idle()
    assert sink.empty()
    assert int(dut.ip_protocol.value) == packet[IP].proto
    assert packet[IP].proto == IP_PROTO_TCP
    assert int(dut.non_udp_drop_count.value) == 1

    await Timer(CLOCK_PERIOD_NS, unit="ns")
    assert sink.empty()


@cocotb.test()
async def udp_then_tcp(dut):
    """Forward a UDP frame, then drop a TCP frame."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    udp_bytes, _ = udp_frame()
    tcp_bytes, _ = tcp_frame()

    frame = await forward_one(source, sink, udp_bytes)
    assert bytes(frame.tdata) == udp_bytes[IP_PAYLOAD_OFFSET:]
    assert int(frame.tuser) == 0

    await drop_one(source, sink, tcp_bytes, dut)
    assert int(dut.non_udp_drop_count.value) == 1


@cocotb.test()
async def tcp_then_udp(dut):
    """Drop a TCP frame, then forward a UDP frame."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    udp_bytes, _ = udp_frame()
    tcp_bytes, _ = tcp_frame()

    await drop_one(source, sink, tcp_bytes, dut)
    assert int(dut.non_udp_drop_count.value) == 1

    frame = await forward_one(source, sink, udp_bytes)
    assert bytes(frame.tdata) == udp_bytes[IP_PAYLOAD_OFFSET:]
    assert int(frame.tuser) == 0


@cocotb.test()
async def two_udp_frames(dut):
    """Forward two consecutive UDP frames."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    udp_bytes, _ = udp_frame()
    for _ in range(2):
        frame = await forward_one(source, sink, udp_bytes)
        assert bytes(frame.tdata) == udp_bytes[IP_PAYLOAD_OFFSET:]
        assert int(frame.tuser) == 0

    assert int(dut.non_udp_drop_count.value) == 0


@cocotb.test()
async def udp_tcp_udp(dut):
    """Forward a UDP frame, drop a TCP frame, then forward a UDP frame again."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    udp_bytes, _ = udp_frame()
    tcp_bytes, _ = tcp_frame()

    frame = await forward_one(source, sink, udp_bytes)
    assert bytes(frame.tdata) == udp_bytes[IP_PAYLOAD_OFFSET:]

    await drop_one(source, sink, tcp_bytes, dut)
    assert int(dut.non_udp_drop_count.value) == 1

    frame = await forward_one(source, sink, udp_bytes)
    assert bytes(frame.tdata) == udp_bytes[IP_PAYLOAD_OFFSET:]
    assert int(dut.non_udp_drop_count.value) == 1
