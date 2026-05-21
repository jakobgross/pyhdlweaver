import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

from examples.eth_ip.eth_ip import IP_PAYLOAD_OFFSET, IP_PROTO_TCP, IP_PROTO_UDP

CLOCK_PERIOD_NS = 10
DATA_WIDTH_BYTES = 64


def _import_scapy_offline():
    """Import packet building Scapy pieces without host network probing."""

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


def udp_frame(load: bytes = b"pyhdlweaver") -> tuple[bytes, Ether]:
    packet = (
        Ether(dst="00:11:22:33:44:55", src="66:77:88:99:aa:bb")
        / IP(src="192.168.1.10", dst="192.168.1.20", flags="DF", id=0x1234)
        / UDP(sport=0x1122, dport=0x3344)
        / Raw(load=load)
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


async def forward_one(source, sink, frame_bytes: bytes) -> AxiStreamFrame:
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    return await sink.recv(compact=False)


async def drop_one(source, sink, frame_bytes: bytes, dut) -> None:
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    for _ in range(20):
        await RisingEdge(dut.clk)
    assert source.idle()
    assert sink.empty()


def frame_tkeep_values(frame: AxiStreamFrame) -> list[int]:
    if frame.tkeep is None:
        return [1] * len(frame.tdata)
    if isinstance(frame.tkeep, int):
        return [(frame.tkeep >> i) & 1 for i in range(DATA_WIDTH_BYTES)]
    return [int(value) for value in frame.tkeep]


def frame_tdest_values(frame: AxiStreamFrame) -> list[int]:
    if frame.tdest is None:
        return [0] * len(frame.tdata)
    if isinstance(frame.tdest, (bool, int)):
        return [int(frame.tdest)] * len(frame.tdata)
    return [int(value) for value in frame.tdest]


def kept_bytes(frame: AxiStreamFrame) -> bytes:
    keep = frame_tkeep_values(frame)
    return bytes(value for value, valid in zip(frame.tdata, keep) if valid)


def assert_only_ip_payload_is_forwarded(frame: AxiStreamFrame, frame_bytes: bytes) -> None:
    keep = frame_tkeep_values(frame)
    payload_len = len(frame_bytes) - IP_PAYLOAD_OFFSET
    assert keep[:payload_len] == [1] * payload_len
    assert keep[payload_len:] == [0] * (len(keep) - payload_len)

    assert kept_bytes(frame) == frame_bytes[IP_PAYLOAD_OFFSET:]
    assert all(value == 0 for value in frame_tdest_values(frame))


@cocotb.test()
async def forwards_only_udp_payload_from_first_512bit_beat(dut):
    """Payload bytes in the parse beat are packed down to output lane 0."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame_bytes, packet = udp_frame()
    frame = await forward_one(source, sink, frame_bytes)

    assert_only_ip_payload_is_forwarded(frame, frame_bytes)
    assert all(int(value) == 0 for value in frame.tuser)
    assert int(dut.ip_protocol.value) == packet[IP].proto
    assert packet[IP].proto == IP_PROTO_UDP
    assert int(dut.non_udp_drop_count.value) == 0


@cocotb.test()
async def forwards_long_udp_payload_after_parse_tail(dut):
    """A stored parse tail is followed by later payload beats without byte loss."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame_bytes, _ = udp_frame(bytes(range(120)))
    frame = await forward_one(source, sink, frame_bytes)

    assert kept_bytes(frame) == frame_bytes[IP_PAYLOAD_OFFSET:]
    assert all(int(value) == 0 for value in frame.tuser)


@cocotb.test()
async def drops_tcp_packet_inside_first_512bit_beat(dut):
    """A dropped frame that ends in the parse beat still increments the counter."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame_bytes, packet = tcp_frame()
    await drop_one(source, sink, frame_bytes, dut)

    assert int(dut.ip_protocol.value) == packet[IP].proto
    assert packet[IP].proto == IP_PROTO_TCP
    assert int(dut.non_udp_drop_count.value) == 1


@cocotb.test()
async def tcp_then_udp_recovers_on_512bit_bus(dut):
    """The parser accepts a clean UDP frame after a one-beat TCP drop."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    tcp_bytes, _ = tcp_frame()
    udp_bytes, _ = udp_frame()

    await drop_one(source, sink, tcp_bytes, dut)
    frame = await forward_one(source, sink, udp_bytes)

    assert_only_ip_payload_is_forwarded(frame, udp_bytes)
    assert all(int(value) == 0 for value in frame.tuser)
    assert int(dut.non_udp_drop_count.value) == 1
