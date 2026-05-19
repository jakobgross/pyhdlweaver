from pyhdlweaver.actions import (
    CaptureAction,
    DropAction,
    DropOnFlag,
    DropOnMismatch,
    DropOnRange,
    DropOnRegisterFlagMismatch,
    DropOnRegisterMatch,
    DropOnRegisterMismatch,
    DropOnRegisterRange,
    LengthAction,
    RouteByRange,
    RouteByRegister,
    RouteByRegistersRange,
    RouteByValue,
    RouteToAll,
)
from pyhdlweaver.generators.code_generator import CodeGenerator
from pyhdlweaver.generators.generated_file import GeneratedFile
from pyhdlweaver.generators.backends.systemverilog.config_port import ConfigPort
from pyhdlweaver.generators.backends.systemverilog.drop_condition import DropCondition
from pyhdlweaver.generators.backends.systemverilog.generation_plan import GenerationPlan
from pyhdlweaver.generators.backends.systemverilog.route_condition import RouteCondition
from pyhdlweaver.generators.backends.systemverilog.template_renderer import TemplateRenderer
from pyhdlweaver.generators.backends.systemverilog.utils import optional_tdest, sv_identifier, sv_int, tdest
from pyhdlweaver.protocols import FixedProtocol, Protocol, SidebandProtocol
from pyhdlweaver.protocols.definitions import Field, StreamLayout
from pyhdlweaver.stream.axi_stream import AxisStream


class SystemVerilogGenerator(CodeGenerator):
    def __init__(self) -> None:
        self.renderer = TemplateRenderer()

    def generate(
        self,
        protocol: Protocol,
        stream: AxisStream,
        module_name: str | None = None,
    ) -> GeneratedFile:
        """Dispatch generation to the subgenerator that matches the protocol kind."""
        if isinstance(protocol, SidebandProtocol):
            from pyhdlweaver.generators.backends.systemverilog.sideband_systemverilog_generator import (
                SidebandSystemVerilogGenerator,
            )

            return SidebandSystemVerilogGenerator().generate(protocol, stream, module_name)
        if isinstance(protocol, FixedProtocol):
            from pyhdlweaver.generators.backends.systemverilog.fixed_systemverilog_generator import (
                FixedSystemVerilogGenerator,
            )

            return FixedSystemVerilogGenerator().generate(protocol, stream, module_name)
        raise NotImplementedError(
            f"SystemVerilog generation is not implemented for {protocol.protocol_kind}"
        )

    def build_plan(
        self,
        protocol: Protocol,
        stream: AxisStream,
        module_name: str | None,
    ) -> GenerationPlan:
        """Derive a GenerationPlan from a protocol and stream, resolving all field actions into typed conditions."""
        layout = StreamLayout(stream, byte_offset=0)
        parse_beats = layout.header_beats(protocol.fields)
        final_beat = parse_beats - 1
        final_beat_fields: set[str] = {
            field_.name
            for field_ in protocol.fields
            if any(beat.beat == final_beat for beat in layout.field_beats(field_))
        }
        config_ports: dict[str, ConfigPort] = {}
        drop_conditions: list[DropCondition] = []
        route_conditions: list[RouteCondition] = []
        default_tdest = 0

        for field_ in protocol.fields:
            for action in field_.actions:
                if isinstance(action, DropAction):
                    drop_conditions.append(
                        DropCondition(
                            expression=self.drop_expression(field_, action, config_ports, final_beat_fields),
                            counter_name=action.counter_name(field_.name),
                        )
                    )
                elif isinstance(action, (RouteByValue, RouteByRange, RouteByRegister, RouteByRegistersRange)):
                    conditions, action_default = self.route_conditions(field_, action, config_ports, final_beat_fields)
                    route_conditions.extend(conditions)
                    if action_default is not None:
                        default_tdest = action_default
                elif isinstance(action, RouteToAll):
                    raise NotImplementedError("RouteToAll cannot be represented by AXI-Stream tdest")
                elif isinstance(action, CaptureAction):
                    raise NotImplementedError("Capture actions are not implemented by the SystemVerilog generator yet")
                elif isinstance(action, LengthAction):
                    raise NotImplementedError("Length actions are not implemented by the SystemVerilog generator yet")
                else:
                    raise NotImplementedError(f"Unsupported action type: {type(action).__name__}")

        return GenerationPlan(
            protocol=protocol,
            stream=stream,
            layout=layout,
            module_name=module_name or f"{protocol.name}_parser",
            parse_beats=parse_beats,
            config_ports=tuple(config_ports.values()),
            drop_conditions=tuple(drop_conditions),
            route_conditions=tuple(route_conditions),
            default_tdest=default_tdest,
        )

    def drop_expression(
        self,
        field_: Field,
        action: DropAction,
        config_ports: dict[str, ConfigPort],
        final_beat_fields: set[str],
    ) -> str:
        """Return a SystemVerilog boolean expression that is true when the field value triggers a drop.

        Fields in final_beat_fields are read via their _comb bypass wire to avoid a
        nonblocking-assignment read-after-write hazard on the last parse beat.
        """
        value = f"{field_.name}_comb" if field_.name in final_beat_fields else f"{field_.name}_reg"
        if isinstance(action, DropOnMismatch):
            expected = sv_int(field_.width, action.expected)
            if action.mask is None:
                return f"({value} != {expected})"
            mask = sv_int(field_.width, action.mask)
            return f"(({value} & {mask}) != ({expected} & {mask}))"
        if isinstance(action, DropOnFlag):
            return f"(({value} & {sv_int(field_.width, action.mask)}) != {field_.width}'d0)"
        if isinstance(action, DropOnRange):
            return (
                f"(({value} < {sv_int(field_.width, action.min_value)}) || "
                f"({value} > {sv_int(field_.width, action.max_value)}))"
            )
        if isinstance(action, (DropOnRegisterMatch, DropOnRegisterMismatch)):
            register = self.config_value(config_ports, action.register, field_.width, action.default_value)
            if action.mask is None:
                comparison = f"({value} == {register})"
            else:
                mask = sv_int(field_.width, action.mask)
                comparison = f"(({value} & {mask}) == ({register} & {mask}))"
            if isinstance(action, DropOnRegisterMatch):
                return comparison
            return f"!{comparison}"
        if isinstance(action, DropOnRegisterFlagMismatch):
            register = self.config_value(config_ports, action.register, field_.width, action.default_value)
            mask = sv_int(field_.width, action.mask)
            return f"(({value} & {mask}) != ({register} & {mask}))"
        if isinstance(action, DropOnRegisterRange):
            min_register = self.config_value(config_ports, action.min_register, field_.width, action.min_default)
            max_register = self.config_value(config_ports, action.max_register, field_.width, action.max_default)
            return f"(({value} < {min_register}) || ({value} > {max_register}))"
        raise NotImplementedError(f"Unsupported drop action: {type(action).__name__}")

    def route_conditions(
        self,
        field_: Field,
        action: RouteByValue | RouteByRange | RouteByRegister | RouteByRegistersRange,
        config_ports: dict[str, ConfigPort],
        final_beat_fields: set[str],
    ) -> tuple[list[RouteCondition], int | None]:
        """Return RouteCondition objects and an optional default tdest for a routing action on field_.

        Fields in final_beat_fields are read via their _comb bypass wire to avoid a
        nonblocking-assignment read-after-write hazard on the last parse beat.
        """
        value = f"{field_.name}_comb" if field_.name in final_beat_fields else f"{field_.name}_reg"
        if isinstance(action, RouteByValue):
            conditions = []
            for match_value, destination in action.table.items():
                route_destination = tdest(destination)
                conditions.append(
                    RouteCondition(
                        expression=f"({value} == {sv_int(field_.width, match_value)})",
                        destination=route_destination,
                        destination_literal=sv_int(4, route_destination),
                    )
                )
            return conditions, optional_tdest(action.default)
        if isinstance(action, RouteByRange):
            conditions = []
            for min_value, max_value, destination in action.ranges:
                route_destination = tdest(destination)
                conditions.append(
                    RouteCondition(
                        expression=(
                            f"(({value} >= {sv_int(field_.width, min_value)}) && "
                            f"({value} <= {sv_int(field_.width, max_value)}))"
                        ),
                        destination=route_destination,
                        destination_literal=sv_int(4, route_destination),
                    )
                )
            return conditions, optional_tdest(action.default)
        if isinstance(action, RouteByRegister):
            register = self.config_value(config_ports, action.register, field_.width, action.default_value)
            if action.mask is None:
                expression = f"({value} == {register})"
            else:
                mask = sv_int(field_.width, action.mask)
                expression = f"(({value} & {mask}) == ({register} & {mask}))"
            destination = tdest(action.destination)
            return [
                RouteCondition(
                    expression=expression,
                    destination=destination,
                    destination_literal=sv_int(4, destination),
                )
            ], optional_tdest(action.default)
        if isinstance(action, RouteByRegistersRange):
            min_register = self.config_value(config_ports, action.min_register, field_.width, action.min_default)
            max_register = self.config_value(config_ports, action.max_register, field_.width, action.max_default)
            destination = tdest(action.destination)
            return [
                RouteCondition(
                    expression=f"(({value} >= {min_register}) && ({value} <= {max_register}))",
                    destination=destination,
                    destination_literal=sv_int(4, destination),
                )
            ], optional_tdest(action.default)
        raise NotImplementedError(f"Unsupported route action: {type(action).__name__}")

    def config_value(
        self,
        config_ports: dict[str, ConfigPort],
        name: str,
        width: int,
        default_value: int | None = None,
    ) -> str:
        """Return the _reg signal name for a config register, creating a ConfigPort entry on first use."""
        port_name = f"cfg_{sv_identifier(name)}"
        config_ports.setdefault(port_name, ConfigPort(name=port_name, width=width, default_value=default_value))
        return f"{port_name}_reg"

    def render_module(self, plan: GenerationPlan, body: str) -> str:
        """Wrap a rendered body string in the module template and return the full file content."""
        return self.renderer.render(
            "module.sv.j2",
            plan=plan,
            body=body,
        )
