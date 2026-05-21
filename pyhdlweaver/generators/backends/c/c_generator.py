from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from pyhdlweaver.actions import (
    DropAction,
    DropOnFlag,
    DropOnMismatch,
    DropOnRange,
    DropOnRegisterFlagMismatch,
    DropOnRegisterMatch,
    DropOnRegisterMismatch,
    DropOnRegisterRange,
    RouteByRange,
    RouteByRegister,
    RouteByRegistersRange,
    RouteByValue,
)
from pyhdlweaver.generators.code_generator import CodeGenerator
from pyhdlweaver.generators.generated_file import GeneratedFile, GeneratedFiles
from pyhdlweaver.protocols import (
    DiscriminatedProtocol,
    FixedProtocol,
    MultiMessageProtocol,
    Protocol,
    SidebandProtocol,
)
from pyhdlweaver.protocols.definitions import Field
from pyhdlweaver.stream.axi_stream import AxisStream


@dataclass(frozen=True)
class CConfigField:
    name: str
    c_type: str
    default: str


@dataclass(frozen=True)
class CField:
    name: str
    offset: int
    width: int
    width_bytes: int
    c_type: str
    is_bytes: bool
    source: Field


@dataclass(frozen=True)
class CVariant:
    value: int
    tag: str
    fields: tuple[CField, ...]
    length: int


class CGenerator(CodeGenerator):
    def __init__(self) -> None:
        template_dir = Path(__file__).resolve().parents[2] / "templates" / "c"
        self.environment = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )

    def generate(
        self,
        protocol: Protocol,
        stream: AxisStream,
        module_name: str | None = None,
    ) -> GeneratedFiles:
        del stream
        name = c_identifier(module_name or f"{protocol.name}_parser")
        context = self.build_context(protocol, name)
        header = self.environment.get_template("header.h.j2").render(**context)
        source = self.environment.get_template("source.c.j2").render(**context)
        return GeneratedFiles(
            files=(
                GeneratedFile(name=f"{name}.h", content=header),
                GeneratedFile(name=f"{name}.c", content=source),
            )
        )

    def build_context(self, protocol: Protocol, module_name: str) -> dict[str, Any]:
        if isinstance(protocol, MultiMessageProtocol):
            outer_fields = c_fields(unique_fields(protocol.fields))
            sub_fields = c_fields(unique_fields(protocol.sub_protocol.fields))
            fields_for_config = tuple(field.source for field in outer_fields + sub_fields)
            return self.base_context(protocol, module_name, fields_for_config) | {
                "kind": "multi",
                "outer_fields": outer_fields,
                "sub_fields": sub_fields,
                "message_count_field": c_identifier(protocol.message_count_field),
                "sub_length_field": c_identifier(protocol.sub_protocol.length_field.name),
                "sub_header_length": protocol.sub_protocol.parse_length,
                "outer_action_lines": self.action_lines(module_name, "result", outer_fields),
            }
        if isinstance(protocol, DiscriminatedProtocol):
            common_fields = c_fields(unique_fields(protocol.fields))
            variants = tuple(
                CVariant(
                    value=value,
                    tag=f"{value:02x}",
                    fields=c_fields(unique_fields(fields)),
                    length=protocol.variant_length[value],  # type: ignore[index]
                )
                for value, fields in sorted(protocol.variants.items())
            )
            variant_config_fields = tuple(field.source for variant in variants for field in variant.fields)
            return self.base_context(
                protocol,
                module_name,
                tuple(field.source for field in common_fields) + variant_config_fields,
            ) | {
                "kind": "discriminated",
                "common_fields": common_fields,
                "variants": variants,
                "discriminator": c_identifier(protocol.discriminator.name),
                "forwards_payload": protocol.forward,
                "common_action_lines": self.action_lines(module_name, "result", common_fields),
            }
        if isinstance(protocol, SidebandProtocol):
            fields = c_fields(unique_fields(protocol.fields))
            return self.base_context(protocol, module_name, tuple(field.source for field in fields)) | {
                "kind": "fixed",
                "fields": fields,
                "forwards_payload": True,
                "action_lines": self.action_lines(module_name, "result", fields),
            }
        if isinstance(protocol, FixedProtocol):
            fields = c_fields(unique_fields(protocol.fields))
            return self.base_context(protocol, module_name, tuple(field.source for field in fields)) | {
                "kind": "fixed",
                "fields": fields,
                "forwards_payload": False,
                "action_lines": self.action_lines(module_name, "result", fields),
            }
        raise NotImplementedError(f"C generation is not implemented for {protocol.protocol_kind}")

    def base_context(
        self,
        protocol: Protocol,
        module_name: str,
        fields: tuple[Field, ...],
    ) -> dict[str, Any]:
        return {
            "module_name": module_name,
            "guard": f"PYHDLWEAVER_GENERATED_{module_name.upper()}_H",
            "upper_name": module_name.upper(),
            "parse_length": protocol.parse_length,
            "config_fields": self.config_fields(fields),
            "uses_byte_copy": any(field.width > 64 for field in fields),
        }

    def action_lines(
        self,
        module_name: str,
        target: str,
        fields: tuple[CField, ...],
    ) -> tuple[str, ...]:
        upper = module_name.upper()
        lines: list[str] = []
        for field in fields:
            value = f"{target}.{field.name}"
            for action in field.source.actions:
                if isinstance(action, DropAction):
                    lines.append(f"if ({self.drop_expression(value, field.width, action)}) {{")
                    lines.append(f"    {target}.error_flags |= {upper}_ERROR_DROPPED;")
                    lines.append("}")
                elif isinstance(action, RouteByValue):
                    for match_value, destination in action.table.items():
                        lines.append(f"if ({value} == {c_literal(field.width, match_value)}) {{")
                        lines.append(f"    {target}.has_destination = true;")
                        lines.append(f"    {target}.destination = {c_destination(destination)}u;")
                        lines.append("}")
                    lines += self.default_route_lines(target, action.default)
                elif isinstance(action, RouteByRange):
                    for min_value, max_value, destination in action.ranges:
                        lines.append(f"if ({range_expression(value, field.width, min_value, max_value)}) {{")
                        lines.append(f"    {target}.has_destination = true;")
                        lines.append(f"    {target}.destination = {c_destination(destination)}u;")
                        lines.append("}")
                    lines += self.default_route_lines(target, action.default)
                elif isinstance(action, RouteByRegister):
                    cfg = c_identifier(action.register)
                    if action.mask is None:
                        comparison = f"{value} == cfg->{cfg}"
                    else:
                        mask = c_literal(field.width, action.mask)
                        comparison = f"({value} & {mask}) == (cfg->{cfg} & {mask})"
                    lines.append(f"if ({comparison}) {{")
                    lines.append(f"    {target}.has_destination = true;")
                    lines.append(f"    {target}.destination = {c_destination(action.destination)}u;")
                    lines.append("}")
                    lines += self.default_route_lines(target, action.default)
                elif isinstance(action, RouteByRegistersRange):
                    min_cfg = c_identifier(action.min_register)
                    max_cfg = c_identifier(action.max_register)
                    lines.append(f"if ({value} >= cfg->{min_cfg} && {value} <= cfg->{max_cfg}) {{")
                    lines.append(f"    {target}.has_destination = true;")
                    lines.append(f"    {target}.destination = {c_destination(action.destination)}u;")
                    lines.append("}")
                    lines += self.default_route_lines(target, action.default)
                else:
                    raise NotImplementedError(f"Unsupported C action: {type(action).__name__}")
        return tuple(lines)

    def default_route_lines(self, target: str, destination: int | str | None) -> list[str]:
        if destination is None:
            return []
        return [
            f"if (!{target}.has_destination) {{",
            f"    {target}.has_destination = true;",
            f"    {target}.destination = {c_destination(destination)}u;",
            "}",
        ]

    def drop_expression(self, value: str, width: int, action: DropAction) -> str:
        if isinstance(action, DropOnMismatch):
            expected = c_literal(width, action.expected)
            if action.mask is None:
                return f"{value} != {expected}"
            mask = c_literal(width, action.mask)
            return f"({value} & {mask}) != ({expected} & {mask})"
        if isinstance(action, DropOnFlag):
            return f"({value} & {c_literal(width, action.mask)}) != 0u"
        if isinstance(action, DropOnRange):
            return outside_range_expression(value, width, action.min_value, action.max_value)
        if isinstance(action, DropOnRegisterMatch):
            return self.register_compare(value, width, action.register, action.mask, equal=True)
        if isinstance(action, DropOnRegisterMismatch):
            return self.register_compare(value, width, action.register, action.mask, equal=False)
        if isinstance(action, DropOnRegisterFlagMismatch):
            cfg = c_identifier(action.register)
            mask = c_literal(width, action.mask)
            return f"({value} & {mask}) != (cfg->{cfg} & {mask})"
        if isinstance(action, DropOnRegisterRange):
            return (
                f"{value} < cfg->{c_identifier(action.min_register)} || "
                f"{value} > cfg->{c_identifier(action.max_register)}"
            )
        raise NotImplementedError(f"Unsupported C drop action: {type(action).__name__}")

    def register_compare(
        self,
        value: str,
        width: int,
        register: str,
        mask: int | None,
        *,
        equal: bool,
    ) -> str:
        cfg = c_identifier(register)
        if mask is None:
            comparison = f"{value} == cfg->{cfg}"
        else:
            mask_literal = c_literal(width, mask)
            comparison = f"({value} & {mask_literal}) == (cfg->{cfg} & {mask_literal})"
        return comparison if equal else f"!({comparison})"

    def config_fields(self, fields: tuple[Field, ...]) -> tuple[CConfigField, ...]:
        configs: dict[str, CConfigField] = {}
        for field in fields:
            for action in field.actions:
                if isinstance(action, (DropOnRegisterMatch, DropOnRegisterMismatch, RouteByRegister)):
                    name = c_identifier(action.register)
                    configs[name] = CConfigField(name, c_uint_type(field.width), c_literal(field.width, action.default_value or 0))
                elif isinstance(action, DropOnRegisterFlagMismatch):
                    name = c_identifier(action.register)
                    configs[name] = CConfigField(name, c_uint_type(field.width), c_literal(field.width, action.default_value or 0))
                elif isinstance(action, DropOnRegisterRange):
                    min_name = c_identifier(action.min_register)
                    max_name = c_identifier(action.max_register)
                    configs[min_name] = CConfigField(min_name, c_uint_type(field.width), c_literal(field.width, action.min_default or 0))
                    configs[max_name] = CConfigField(max_name, c_uint_type(field.width), c_literal(field.width, action.max_default or 0))
                elif isinstance(action, RouteByRegistersRange):
                    min_name = c_identifier(action.min_register)
                    max_name = c_identifier(action.max_register)
                    configs[min_name] = CConfigField(min_name, c_uint_type(field.width), c_literal(field.width, action.min_default or 0))
                    configs[max_name] = CConfigField(max_name, c_uint_type(field.width), c_literal(field.width, action.max_default or 0))
        return tuple(configs.values())


def c_fields(fields: tuple[Field, ...]) -> tuple[CField, ...]:
    return tuple(
        CField(
            name=c_identifier(field.name),
            offset=field.offset,
            width=field.width,
            width_bytes=field.width_bytes,
            c_type="uint8_t" if field.width > 64 else c_uint_type(field.width),
            is_bytes=field.width > 64,
            source=field,
        )
        for field in fields
    )


def c_identifier(name: str) -> str:
    return "".join(char if char.isalnum() or char == "_" else "_" for char in name)


def c_uint_type(width: int) -> str:
    if width <= 8:
        return "uint8_t"
    if width <= 16:
        return "uint16_t"
    if width <= 32:
        return "uint32_t"
    if width <= 64:
        return "uint64_t"
    raise ValueError("fields wider than 64 bits must be stored as byte arrays")


def c_literal(width: int, value: int) -> str:
    suffix = "ULL" if width > 32 else "u"
    return f"0x{value:x}{suffix}"


def c_destination(destination: int | str) -> int:
    if not isinstance(destination, int):
        raise NotImplementedError("C route destinations must be integers")
    if destination < 0:
        raise ValueError("C route destinations must be non-negative")
    return destination


def max_field_value(width: int) -> int:
    return (1 << width) - 1 if width < 64 else (1 << 64) - 1


def range_expression(value: str, width: int, min_value: int, max_value: int) -> str:
    conditions: list[str] = []
    if min_value > 0:
        conditions.append(f"(uint64_t){value} >= {c_literal(width, min_value)}")
    if max_value < max_field_value(width):
        conditions.append(f"(uint64_t){value} <= {c_literal(width, max_value)}")
    return " && ".join(conditions) if conditions else "true"


def outside_range_expression(value: str, width: int, min_value: int, max_value: int) -> str:
    conditions: list[str] = []
    if min_value > 0:
        conditions.append(f"(uint64_t){value} < {c_literal(width, min_value)}")
    if max_value < max_field_value(width):
        conditions.append(f"(uint64_t){value} > {c_literal(width, max_value)}")
    return " || ".join(conditions) if conditions else "false"


def unique_fields(fields: tuple[Field, ...] | list[Field]) -> tuple[Field, ...]:
    seen: set[tuple[str, int, int]] = set()
    result: list[Field] = []
    for field in fields:
        key = (field.name, field.offset, field.width)
        if key in seen:
            continue
        seen.add(key)
        result.append(field)
    return tuple(result)
