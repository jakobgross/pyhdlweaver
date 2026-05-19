"""
UDP protocol definitions used as generator inputs.

Two parsers are defined here:
- UDP_PORT_ROUTER: 8-bit bus, routes by a configurable destination port register.
- UDP_CLASSIFIER_64: 64-bit bus, drops non-IPv4, non-UDP, wrong destination IP,
  out-of-range source port, and zero-checksum frames, then routes by destination
  port range to three well-known, registered categories.
"""
from pyhdlweaver.actions import (
    DropOnMismatch,
    DropOnRegisterMatch,
    DropOnRegisterMismatch,
    DropOnRegisterRange,
    RouteByRange,
    RouteByRegister,
)
from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols import SidebandProtocol

UDP_PAYLOAD_OFFSET = 42  # Eth(14) + IP(20) + UDP header(8)
DEFAULT_DST_PORT = 1234

# UDP_CLASSIFIER_64 defaults
DEFAULT_ALLOWED_DST_IP = 0xC0A80101  # 192.168.1.1
DEFAULT_MIN_SPORT = 1024
DEFAULT_MAX_SPORT = 65535
DEFAULT_BLOCKED_CHECKSUM = 0  # drop zero-checksum UDP (RFC 768 "no checksum")

UDP_DPORT = Field(
    "udp_dport",
    offset=36,
    width=16,
    actions=[RouteByRegister(register="dst_port", destination=0, default=1, default_value=DEFAULT_DST_PORT)],
)

UDP_PORT_ROUTER = SidebandProtocol(
    name="udp_port_router",
    fields=[UDP_DPORT],
    total_length=UDP_PAYLOAD_OFFSET,
)

UDP_CLASSIFIER_64_FIELDS = [
    Field(
        "ethertype",
        offset=12,
        width=16,
        actions=[DropOnMismatch(expected=0x0800, counter="non_ipv4_drop_count")],
    ),
    Field(
        "ip_protocol",
        offset=23,
        width=8,
        actions=[DropOnMismatch(expected=0x11, counter="non_udp_drop_count")],
    ),
    Field(
        "ip_dst",
        offset=30,
        width=32,
        actions=[DropOnRegisterMismatch(register="allowed_dst_ip", default_value=DEFAULT_ALLOWED_DST_IP)],
    ),
    Field(
        "udp_sport",
        offset=34,
        width=16,
        actions=[DropOnRegisterRange(
            min_register="min_sport",
            max_register="max_sport",
            min_default=DEFAULT_MIN_SPORT,
            max_default=DEFAULT_MAX_SPORT,
        )],
    ),
    Field(
        "udp_dport",
        offset=36,
        width=16,
        actions=[RouteByRange(ranges=[(1, 1023, 0), (1024, 49151, 1), (49152, 65535, 2)], default=3)],
    ),
    Field(
        "udp_checksum",
        offset=40,
        width=16,
        actions=[DropOnRegisterMatch(register="blocked_checksum", default_value=DEFAULT_BLOCKED_CHECKSUM)],
    ),
]

UDP_CLASSIFIER_64 = SidebandProtocol(
    name="udp_classifier_64",
    fields=UDP_CLASSIFIER_64_FIELDS,
    total_length=UDP_PAYLOAD_OFFSET,
)
