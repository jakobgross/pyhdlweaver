from pyhdlweaver.actions import DropOnMismatch, RouteByValue
from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols import SidebandProtocol

ETH_HEADER_SIZE = 14

# dst_mac (0-5) and src_mac (6-11) are skipped, always addressed to us
ETH_ETHERTYPE = Field("eth_ethertype", offset=12, width=16)

ETH_FIELDS = [ETH_ETHERTYPE]

ETHERTYPE_IPV4 = 0x0800
ETHERTYPE_ARP  = 0x0806
ETHERTYPE_IPV6 = 0x86DD
ETHERTYPE_VLAN = 0x8100

IP_HEADER_OFFSET = ETH_HEADER_SIZE  # 14
IP_HEADER_SIZE   = 20               # IHL=5, no options

IP_VERSION_IHL  = Field("ip_version_ihl",  offset=14, width=8)   # version[7:4] ihl[3:0]
IP_TOTAL_LENGTH = Field("ip_total_length", offset=16, width=16)
IP_FLAGS_FRAG   = Field("ip_flags_frag",   offset=20, width=16)  # flags[15:13] frag_offset[12:0]
IP_PROTOCOL     = Field("ip_protocol",     offset=23, width=8)
IP_SRC          = Field("ip_src",          offset=26, width=32)
IP_DST          = Field("ip_dst",          offset=30, width=32)

IP_FIELDS = [
    IP_VERSION_IHL,
    IP_TOTAL_LENGTH,
    IP_FLAGS_FRAG,
    IP_PROTOCOL,
    IP_SRC,
    IP_DST,
]

ETH_IP_FIELDS    = ETH_FIELDS + IP_FIELDS
IP_PAYLOAD_OFFSET = IP_HEADER_OFFSET + IP_HEADER_SIZE  # 34

IP_PROTO_ICMP = 0x01
IP_PROTO_TCP  = 0x06
IP_PROTO_UDP  = 0x11

IP_VERSION_4      = 4
IP_IHL_NO_OPTIONS = 5

IP_FLAG_MF_BIT      = 13
IP_FLAG_DF_BIT      = 14
IP_FRAG_OFFSET_MASK = 0x1FFF

IP_PARSER = SidebandProtocol(
    name="eth_ip",
    fields=ETH_IP_FIELDS,
    total_length=IP_PAYLOAD_OFFSET,
)

IP_FORWARD_UDP_FIELDS = ETH_IP_FIELDS.copy()
IP_FORWARD_UDP_FIELDS[IP_FORWARD_UDP_FIELDS.index(IP_PROTOCOL)] = IP_PROTOCOL.with_actions(
    DropOnMismatch(expected=IP_PROTO_UDP, counter="non_udp_drop_count")
)

IP_FORWARD_UDP_PARSER = SidebandProtocol(
    name="eth_ip_forward_udp",
    fields=IP_FORWARD_UDP_FIELDS,
    total_length=IP_PAYLOAD_OFFSET,
)

IP_BROADCAST = 0xFFFFFFFF

# Broadcast -> tdest 0, UDP -> tdest 1, everything else -> tdest 3.
# ip_dst is captured on the final parse beat on a 32-bit bus (bytes 32-33 land on
# beat 8 = PARSE_BEATS-1), so the _comb bypass path is exercised for its route check.
IP_ROUTE_BROADCAST_UDP_FIELDS = ETH_FIELDS + [
    IP_VERSION_IHL,
    IP_TOTAL_LENGTH,
    IP_FLAGS_FRAG,
    IP_PROTOCOL.with_actions(RouteByValue(table={IP_PROTO_UDP: 1})),
    IP_SRC,
    IP_DST.with_actions(RouteByValue(table={IP_BROADCAST: 0}, default=3)),
]

IP_ROUTE_BROADCAST_UDP_PARSER = SidebandProtocol(
    name="eth_ip_route_broadcast_udp",
    fields=IP_ROUTE_BROADCAST_UDP_FIELDS,
    total_length=IP_PAYLOAD_OFFSET,
)
