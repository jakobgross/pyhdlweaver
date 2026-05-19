import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

CLOCK_PERIOD_NS = 10
DATA_WIDTH_BYTES = 8
PARSE_BYTES = 48  # 6 parse beats x 8 bytes/beat

DEFAULT_SPORT = 1234
DEFAULT_IP_DST = "192.168.1.1"  # matches DEFAULT_ALLOWED_DST_IP (0xC0A80101)

TDEST_WELL_KNOWN = 0   # dport 1-1023
TDEST_REGISTERED = 1   # dport 1024-49151
TDEST_EPHEMERAL  = 2   # dport 49152-65535
TDEST_DEFAULT    = 3   # dport 0 (outside all ranges)


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
    dut.config_valid.value = 0
    dut.cfg_allowed_dst_ip.value = 0
    dut.cfg_min_sport.value = 0
    dut.cfg_max_sport.value = 0
    dut.cfg_blocked_checksum.value = 0

    for _ in range(4):
        await RisingEdge(dut.clk)

    dut.rst.value = 0
    await RisingEdge(dut.clk)


def make_frame(dport: int, sport: int = DEFAULT_SPORT, ip_dst: str = DEFAULT_IP_DST) -> bytes:
    packet = (
        Ether(dst="ff:ff:ff:ff:ff:ff", src="00:11:22:33:44:55")
        / IP(src="10.0.0.1", dst=ip_dst, flags="DF", id=0x1234)
        / UDP(sport=sport, dport=dport)
        / Raw(load=b"pyhdlweaver_test")
    )
    return raw(packet)


async def send_and_recv(dut, frame_bytes: bytes) -> AxiStreamFrame:
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    return await sink.recv()


async def send_and_drop(dut, frame_bytes: bytes):
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    for _ in range(len(frame_bytes) // DATA_WIDTH_BYTES + 8):
        await RisingEdge(dut.clk)
    return source, sink


@cocotb.test()
async def routes_well_known_port_to_tdest_0(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    frame_bytes = make_frame(dport=80)
    frame = await send_and_recv(dut, frame_bytes)
    assert bytes(frame.tdata) == frame_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_WELL_KNOWN
    assert int(frame.tuser) == 0


@cocotb.test()
async def routes_registered_port_to_tdest_1(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    frame_bytes = make_frame(dport=8080)
    frame = await send_and_recv(dut, frame_bytes)
    assert bytes(frame.tdata) == frame_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_REGISTERED
    assert int(frame.tuser) == 0


@cocotb.test()
async def routes_ephemeral_port_to_tdest_2(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    frame_bytes = make_frame(dport=50000)
    frame = await send_and_recv(dut, frame_bytes)
    assert bytes(frame.tdata) == frame_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_EPHEMERAL
    assert int(frame.tuser) == 0


@cocotb.test()
async def routes_port_zero_to_default_tdest_3(dut):
    # dport=0 falls outside all configured ranges, so the default route applies.
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    frame_bytes = make_frame(dport=0)
    frame = await send_and_recv(dut, frame_bytes)
    assert bytes(frame.tdata) == frame_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_DEFAULT
    assert int(frame.tuser) == 0


@cocotb.test()
async def drops_non_ipv4_packet(dut):
    # Patch ethertype to 0x0806 (ARP); all other fields remain valid.
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    frame_bytes = bytearray(make_frame(dport=80))
    frame_bytes[12] = 0x08
    frame_bytes[13] = 0x06
    frame_bytes = bytes(frame_bytes)
    source, sink = await send_and_drop(dut, frame_bytes)
    assert source.idle()
    assert sink.empty()
    assert int(dut.non_ipv4_drop_count.value) == 1


@cocotb.test()
async def drops_non_udp_protocol(dut):
    # TCP packet with seq=0xABCDEF00 so bytes 40-41 are 0xEF,0x00 (non-zero),
    # keeping the checksum filter from firing alongside the protocol drop.
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    packet = (
        Ether(dst="ff:ff:ff:ff:ff:ff", src="00:11:22:33:44:55")
        / IP(src="10.0.0.1", dst=DEFAULT_IP_DST, flags="DF", id=0x1234)
        / TCP(sport=DEFAULT_SPORT, dport=80, seq=0xABCDEF00)
        / Raw(load=b"pyhdlweaver_test")
    )
    frame_bytes = raw(packet)
    source, sink = await send_and_drop(dut, frame_bytes)
    assert source.idle()
    assert sink.empty()
    assert int(dut.non_udp_drop_count.value) == 1


@cocotb.test()
async def drops_wrong_dst_ip(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    frame_bytes = make_frame(dport=80, ip_dst="10.0.0.2")
    source, sink = await send_and_drop(dut, frame_bytes)
    assert source.idle()
    assert sink.empty()
    assert int(dut.ip_dst_register_mismatch_count.value) == 1


@cocotb.test()
async def drops_sport_below_min(dut):
    # sport=80 is below the default min_sport=1024.
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    frame_bytes = make_frame(dport=80, sport=80)
    source, sink = await send_and_drop(dut, frame_bytes)
    assert source.idle()
    assert sink.empty()
    assert int(dut.udp_sport_register_range_count.value) == 1


@cocotb.test()
async def drops_zero_checksum(dut):
    # Zero bytes 40-41 after scapy builds the frame to force udp_checksum=0,
    # which matches the default blocked_checksum register value.
    # This also exercises the comb bypass on the 64-bit final parse beat.
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    frame_bytes = bytearray(make_frame(dport=80))
    frame_bytes[40] = 0x00
    frame_bytes[41] = 0x00
    frame_bytes = bytes(frame_bytes)
    source, sink = await send_and_drop(dut, frame_bytes)
    assert source.idle()
    assert sink.empty()
    assert int(dut.udp_checksum_register_match_count.value) == 1


async def forward_one(source, sink, frame_bytes: bytes) -> AxiStreamFrame:
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    return await sink.recv()


async def drop_one(source, sink, frame_bytes: bytes, dut) -> None:
    await source.send(AxiStreamFrame(frame_bytes, tuser=0))
    for _ in range(len(frame_bytes) // DATA_WIDTH_BYTES + 8):
        await RisingEdge(dut.clk)
    assert source.idle()
    assert sink.empty()


@cocotb.test()
async def ok_then_nok(dut):
    """Forward a valid frame, then drop a frame with sport below min."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    ok_bytes = make_frame(dport=80)
    nok_bytes = make_frame(dport=80, sport=80)

    frame = await forward_one(source, sink, ok_bytes)
    assert bytes(frame.tdata) == ok_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_WELL_KNOWN

    await drop_one(source, sink, nok_bytes, dut)
    assert int(dut.udp_sport_register_range_count.value) == 1


@cocotb.test()
async def nok_then_ok(dut):
    """Drop a frame with wrong ip_dst, then forward a valid frame."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    ok_bytes = make_frame(dport=8080)
    nok_bytes = make_frame(dport=80, ip_dst="10.0.0.2")

    await drop_one(source, sink, nok_bytes, dut)
    assert int(dut.ip_dst_register_mismatch_count.value) == 1

    frame = await forward_one(source, sink, ok_bytes)
    assert bytes(frame.tdata) == ok_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_REGISTERED


@cocotb.test()
async def two_ok_frames(dut):
    """Forward two consecutive valid frames to different tdests."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    frame_a = make_frame(dport=80)
    frame_b = make_frame(dport=50000)

    frame = await forward_one(source, sink, frame_a)
    assert bytes(frame.tdata) == frame_a[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_WELL_KNOWN

    frame = await forward_one(source, sink, frame_b)
    assert bytes(frame.tdata) == frame_b[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_EPHEMERAL


@cocotb.test()
async def ok_nok_ok(dut):
    """Forward, drop (zero checksum), forward to verify state machine resets correctly."""
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis"), dut.clk, dut.rst)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis"), dut.clk, dut.rst)
    await reset_dut(dut)

    ok_bytes = make_frame(dport=8080)
    nok_raw = bytearray(make_frame(dport=8080))
    nok_raw[40] = 0x00
    nok_raw[41] = 0x00
    nok_bytes = bytes(nok_raw)

    frame = await forward_one(source, sink, ok_bytes)
    assert bytes(frame.tdata) == ok_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_REGISTERED

    await drop_one(source, sink, nok_bytes, dut)
    assert int(dut.udp_checksum_register_match_count.value) == 1

    frame = await forward_one(source, sink, ok_bytes)
    assert bytes(frame.tdata) == ok_bytes[PARSE_BYTES:]
    assert int(frame.tdest) == TDEST_REGISTERED
    assert int(dut.udp_checksum_register_match_count.value) == 1
