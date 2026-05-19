from dataclasses import dataclass

from pyhdlweaver.generators.backends.systemverilog.config_port import ConfigPort
from pyhdlweaver.generators.backends.systemverilog.drop_condition import DropCondition
from pyhdlweaver.generators.backends.systemverilog.route_condition import RouteCondition
from pyhdlweaver.protocols import Protocol
from pyhdlweaver.protocols.definitions import StreamLayout
from pyhdlweaver.stream.axi_stream import AxisStream


@dataclass(frozen=True)
class GenerationPlan:
    protocol: Protocol
    stream: AxisStream
    layout: StreamLayout
    module_name: str
    parse_beats: int
    config_ports: tuple[ConfigPort, ...] = ()
    drop_conditions: tuple[DropCondition, ...] = ()
    route_conditions: tuple[RouteCondition, ...] = ()
    default_tdest: int = 0
