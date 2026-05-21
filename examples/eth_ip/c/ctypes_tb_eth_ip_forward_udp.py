import ctypes
from pathlib import Path

from examples.eth_ip.eth_ip import IP_PAYLOAD_OFFSET, IP_PROTO_TCP, IP_PROTO_UDP

SO_PATH = Path(__file__).with_name("eth_ip_forward_udp.so")


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


Ether, IP, Raw, TCP, UDP, raw = import_scapy_offline()


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


class EthIpForwardUdpConfig(ctypes.Structure):
    _fields_ = [("unused", ctypes.c_uint8)]


class EthIpForwardUdpResult(ctypes.Structure):
    _fields_ = [
        ("eth_ethertype", ctypes.c_uint16),
        ("ip_version_ihl", ctypes.c_uint8),
        ("ip_total_length", ctypes.c_uint16),
        ("ip_flags_frag", ctypes.c_uint16),
        ("ip_protocol", ctypes.c_uint8),
        ("ip_src", ctypes.c_uint32),
        ("ip_dst", ctypes.c_uint32),
        ("forwarded", ByteSlice),
        ("ok", ctypes.c_bool),
        ("error_flags", ctypes.c_uint32),
        ("has_destination", ctypes.c_bool),
        ("destination", ctypes.c_uint32),
    ]


def load_parser() -> ctypes.CDLL:
    lib = ctypes.CDLL(str(SO_PATH))
    lib.eth_ip_forward_udp_parse.argtypes = [ByteSlice, ctypes.POINTER(EthIpForwardUdpConfig)]
    lib.eth_ip_forward_udp_parse.restype = EthIpForwardUdpResult
    return lib


def make_frame(proto: str) -> bytes:
    transport = UDP(sport=0x1122, dport=0x3344) if proto == "udp" else TCP(sport=0x1122, dport=0x3344)
    packet = (
        Ether(dst="00:11:22:33:44:55", src="66:77:88:99:aa:bb")
        / IP(src="192.168.1.10", dst="192.168.1.20", flags="DF", id=0x1234)
        / transport
        / Raw(load=b"pyhdlweaver")
    )
    return raw(packet)


def test_forwards_udp_packet():
    lib = load_parser()
    frame = make_frame("udp")
    _buffer, input_view = as_input(frame)
    result = lib.eth_ip_forward_udp_parse(input_view, None)

    assert result.ok
    assert result.ip_protocol == IP_PROTO_UDP
    assert result.error_flags == 0
    assert slice_bytes(result.forwarded) == frame[IP_PAYLOAD_OFFSET:]


def test_drops_tcp_packet():
    lib = load_parser()
    frame = make_frame("tcp")
    _buffer, input_view = as_input(frame)
    result = lib.eth_ip_forward_udp_parse(input_view, None)

    assert not result.ok
    assert result.ip_protocol == IP_PROTO_TCP
    assert result.error_flags & (1 << 1)
    assert slice_bytes(result.forwarded) == b""
