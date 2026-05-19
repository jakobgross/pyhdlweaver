from pyhdlweaver.actions import RouteByRegister
from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols import SidebandProtocol

UDP_PAYLOAD_OFFSET = 42  # Eth(14) + IP(20) + UDP header(8)
DEFAULT_DST_PORT = 1234

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
