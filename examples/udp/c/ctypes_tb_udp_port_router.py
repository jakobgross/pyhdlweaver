import ctypes
from pathlib import Path

from examples.udp.udp import DEFAULT_DST_PORT

SO_PATH = Path(__file__).with_name("udp_port_router.so")


def import_scapy_offline():
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


Ether, IP, Raw, _TCP, UDP, raw = import_scapy_offline()


class ByteSlice(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_uint8)),
        ("length", ctypes.c_size_t),
    ]


def as_input(data: bytes) -> tuple[ctypes.Array, ByteSlice]:
    buffer = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
    return buffer, ByteSlice(buffer, len(data))


def slice_bytes(view: ByteSlice) -> bytes:
    if not view.data or view.length == 0:
        return b""
    return ctypes.string_at(view.data, view.length)


class UdpPortRouterConfig(ctypes.Structure):
    _fields_ = [("dst_port", ctypes.c_uint16)]


class UdpPortRouterResult(ctypes.Structure):
    _fields_ = [
        ("udp_dport", ctypes.c_uint16),
        ("udp_length", ctypes.c_uint16),
        ("udp_checksum", ctypes.c_uint16),
        ("forwarded", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
        ("has_destination", ctypes.c_bool),
        ("destination", ctypes.c_uint32),
    ]


def load_parser() -> ctypes.CDLL:
    lib = ctypes.CDLL(str(SO_PATH))
    lib.udp_port_router_default_config.restype = UdpPortRouterConfig
    lib.udp_port_router_parse.argtypes = [ByteSlice, ctypes.POINTER(UdpPortRouterConfig)]
    lib.udp_port_router_parse.restype = UdpPortRouterResult
    return lib


def make_frame(dport: int) -> bytes:
    packet = (
        Ether(dst="ff:ff:ff:ff:ff:ff", src="00:11:22:33:44:55")
        / IP(src="10.0.0.1", dst="10.0.0.2", flags="DF", id=0x1234)
        / UDP(sport=9999, dport=dport)
        / Raw(load=b"pyhdlweaver")
    )
    return raw(packet)


def test_routes_matching_port_to_destination_0():
    lib = load_parser()
    frame = make_frame(DEFAULT_DST_PORT)
    _buffer, input_view = as_input(frame)
    result = lib.udp_port_router_parse(input_view, None)

    assert result.ok
    assert result.udp_dport == DEFAULT_DST_PORT
    assert result.has_destination
    assert result.destination == 0
    assert slice_bytes(result.forwarded) == frame[42:]


def test_routes_other_port_to_destination_1():
    lib = load_parser()
    frame = make_frame(5678)
    _buffer, input_view = as_input(frame)
    result = lib.udp_port_router_parse(input_view, None)

    assert result.ok
    assert result.has_destination
    assert result.destination == 1


def test_routes_matching_port_after_reconfiguration():
    lib = load_parser()
    config = UdpPortRouterConfig(dst_port=5678)
    frame = make_frame(5678)
    _buffer, input_view = as_input(frame)
    result = lib.udp_port_router_parse(input_view, ctypes.byref(config))

    assert result.ok
    assert result.destination == 0
