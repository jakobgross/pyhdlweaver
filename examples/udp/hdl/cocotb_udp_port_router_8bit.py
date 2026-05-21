import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

from examples.udp.udp import DEFAULT_DST_PORT

CLOCK_PERIOD_NS = 10
DATA_WIDTH_BYTES = 1

# last parsed field: udp_checksum at offset 40, width 16 => parse beats = 42
PARSE_BYTES = 42

TDEST_MATCH = 0
TDEST_OTHER = 1


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
    from scapy.layers.inet import IP, UDP
    from scapy.layers.l2 import Ether
    from scapy.packet import Raw

    return Ether, IP, Raw, UDP, scapy_raw


Ether, IP, Raw, UDP, raw = _import_scapy_offline()


async def reset_dut(dut) -> None:
    dut.rst.value = 1
    dut.config_valid.value = 0
    dut.cfg_dst_port.value = 0

    for _ in range(4):
        await RisingEdge(dut.clk)

    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def configure_dst_port(dut, port: int) -> None:
    """Pulse config_valid for one clock to latch a new destination port into cfg_dst_port_reg."""
    dut.cfg_dst_port.value = port
    dut.config_valid.value = 1
    await RisingEdge(dut.clk)
    dut.config_valid.value = 0
    dut.cfg_dst_port.value = 0


async def send_frame(dut, frame_bytes: bytes) -> AxiStreamFrame:
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)

    await reset_dut(dut)
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))

    return await sink.recv()


def make_frame(dport: int) -> bytes:
    packet = (
        Ether(dst="ff:ff:ff:ff:ff:ff", src="00:11:22:33:44:55")
        / IP(src="10.0.0.1", dst="10.0.0.2", flags="DF", id=0x1234)
        / UDP(sport=9999, dport=dport)
        / Raw(load=b"pyhdlweaver")
    )
    return raw(packet)


@cocotb.test()
async def routes_matching_port_to_tdest_0(dut):
    # After reset, cfg_dst_port_reg holds the default value (1234).
    # A packet to that port should be routed to tdest 0.
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes = make_frame(dport=DEFAULT_DST_PORT)
    frame = await send_frame(dut, frame_bytes)

    assert bytes(frame.tdata) == frame_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_MATCH
    assert int(frame.tuser) == 0
    assert int(dut.udp_dport.value) == DEFAULT_DST_PORT
    assert int(dut.cfg_dst_port_reg.value) == DEFAULT_DST_PORT


@cocotb.test()
async def routes_other_port_to_tdest_1(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes = make_frame(dport=5678)
    frame = await send_frame(dut, frame_bytes)

    assert bytes(frame.tdata) == frame_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_OTHER
    assert int(frame.tuser) == 0


@cocotb.test()
async def routes_matching_port_after_reconfiguration(dut):
    # Reconfigure the match port to 5678, then verify a packet to 5678 goes to tdest 0.
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes = make_frame(dport=5678)
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)

    await reset_dut(dut)
    await configure_dst_port(dut, 5678)
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    frame = await sink.recv()

    assert bytes(frame.tdata) == frame_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_MATCH
    # After the frame completes, both the config and field registers are stable.
    assert int(dut.cfg_dst_port_reg.value) == 5678
    assert int(dut.udp_dport.value) == 5678


@cocotb.test()
async def does_not_route_old_port_after_reconfiguration(dut):
    # After reconfiguring to 5678, the previous default port 1234 must go to tdest 1.
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())

    frame_bytes = make_frame(dport=DEFAULT_DST_PORT)
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)

    await reset_dut(dut)
    await configure_dst_port(dut, 5678)
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    frame = await sink.recv()

    assert bytes(frame.tdata) == frame_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_OTHER


async def route_one(source, sink, frame_bytes: bytes) -> AxiStreamFrame:
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    return await sink.recv()


@cocotb.test()
async def matching_then_other(dut):
    """Route a matching-port frame to tdest 0, then an other-port frame to tdest 1."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    matching = make_frame(dport=DEFAULT_DST_PORT)
    other = make_frame(dport=5678)

    frame = await route_one(source, sink, matching)
    assert bytes(frame.tdata) == matching[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_MATCH

    frame = await route_one(source, sink, other)
    assert int(frame.tdest) == TDEST_OTHER


@cocotb.test()
async def other_then_matching(dut):
    """Route an other-port frame to tdest 1, then a matching-port frame to tdest 0."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    matching = make_frame(dport=DEFAULT_DST_PORT)
    other = make_frame(dport=5678)

    frame = await route_one(source, sink, other)
    assert int(frame.tdest) == TDEST_OTHER

    frame = await route_one(source, sink, matching)
    assert bytes(frame.tdata) == matching[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_MATCH


@cocotb.test()
async def two_matching_frames(dut):
    """Route two consecutive matching-port frames to tdest 0."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    matching = make_frame(dport=DEFAULT_DST_PORT)
    for _ in range(2):
        frame = await route_one(source, sink, matching)
        assert bytes(frame.tdata) == matching[PARSE_BYTES:]
        assert int(frame.tdest) == TDEST_MATCH


@cocotb.test()
async def matching_other_matching(dut):
    """Route matching to tdest 0, other to tdest 1, then matching to tdest 0 again."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    matching = make_frame(dport=DEFAULT_DST_PORT)
    other = make_frame(dport=5678)

    frame = await route_one(source, sink, matching)
    assert bytes(frame.tdata) == matching[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_MATCH

    frame = await route_one(source, sink, other)
    assert int(frame.tdest) == TDEST_OTHER

    frame = await route_one(source, sink, matching)
    assert bytes(frame.tdata) == matching[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_MATCH
