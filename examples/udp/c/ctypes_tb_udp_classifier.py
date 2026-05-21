import ctypes
from pathlib import Path

SO_PATH = Path(__file__).with_name("udp_classifier.so")


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


class UdpClassifierConfig(ctypes.Structure):
    _fields_ = [
        ("allowed_dst_ip", ctypes.c_uint32),
        ("min_sport", ctypes.c_uint16),
        ("max_sport", ctypes.c_uint16),
        ("blocked_checksum", ctypes.c_uint16),
    ]


class UdpClassifierResult(ctypes.Structure):
    _fields_ = [
        ("ethertype", ctypes.c_uint16),
        ("ip_protocol", ctypes.c_uint8),
        ("ip_dst", ctypes.c_uint32),
        ("udp_sport", ctypes.c_uint16),
        ("udp_dport", ctypes.c_uint16),
        ("udp_checksum", ctypes.c_uint16),
        ("forwarded", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
        ("has_destination", ctypes.c_bool),
        ("destination", ctypes.c_uint32),
    ]


def load_parser() -> ctypes.CDLL:
    lib = ctypes.CDLL(str(SO_PATH))
    lib.udp_classifier_parse.argtypes = [ByteSlice, ctypes.POINTER(UdpClassifierConfig)]
    lib.udp_classifier_parse.restype = UdpClassifierResult
    return lib


def make_frame(dport: int, sport: int = 1234, ip_dst: str = "192.168.1.1") -> bytes:
    packet = (
        Ether(dst="ff:ff:ff:ff:ff:ff", src="00:11:22:33:44:55")
        / IP(src="10.0.0.1", dst=ip_dst, flags="DF", id=0x1234)
        / UDP(sport=sport, dport=dport)
        / Raw(load=b"pyhdlweaver_test")
    )
    return raw(packet)


def test_routes_port_ranges():
    lib = load_parser()
    for dport, destination in [(80, 0), (8080, 1), (50000, 2), (0, 3)]:
        frame = make_frame(dport)
        _buffer, input_view = as_input(frame)
        result = lib.udp_classifier_parse(input_view, None)

        assert result.ok
        assert result.has_destination
        assert result.destination == destination
        assert slice_bytes(result.forwarded) == frame[42:]


def test_drops_zero_checksum():
    lib = load_parser()
    frame = bytearray(make_frame(80))
    frame[40] = 0
    frame[41] = 0
    _buffer, input_view = as_input(bytes(frame))
    result = lib.udp_classifier_parse(input_view, None)

    assert not result.ok
    assert result.error_flags & (1 << 1)
    assert slice_bytes(result.forwarded) == b""


def test_drops_wrong_dst_ip():
    lib = load_parser()
    frame = make_frame(80, ip_dst="10.0.0.2")
    _buffer, input_view = as_input(frame)
    result = lib.udp_classifier_parse(input_view, None)

    assert not result.ok
    assert result.error_flags & (1 << 1)
