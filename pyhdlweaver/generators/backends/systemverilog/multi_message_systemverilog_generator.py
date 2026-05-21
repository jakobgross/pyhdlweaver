from dataclasses import dataclass

from pyhdlweaver.generators.generated_file import GeneratedFile
from pyhdlweaver.generators.backends.systemverilog.field_extract_emitter import FieldExtractEmitter
from pyhdlweaver.generators.backends.systemverilog.generation_plan import GenerationPlan
from pyhdlweaver.generators.backends.systemverilog.systemverilog_generator import SystemVerilogGenerator
from pyhdlweaver.generators.backends.systemverilog.utils import counter_width, sv_identifier, sv_int
from pyhdlweaver.protocols import Protocol
from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols.discriminated_protocol import DiscriminatedProtocol
from pyhdlweaver.protocols.length_prefixed_discriminated_sub_protocol import LengthPrefixedDiscriminatedSubProtocol
from pyhdlweaver.protocols.length_prefixed_protocol import LengthPrefixedProtocol
from pyhdlweaver.protocols.multi_message_protocol import MultiMessageProtocol
from pyhdlweaver.protocols.definitions import StreamLayout
from pyhdlweaver.stream.axi_stream import AxisStream


@dataclass(frozen=True)
class _VariantByteEntry:
    key_literals: tuple[str, ...]
    assignments: tuple[str, ...]


@dataclass(frozen=True)
class _ItchByteEntry:
    offset: int
    common: tuple[str, ...]
    variant_entries: tuple[_VariantByteEntry, ...]


@dataclass(frozen=True)
class _VariantFieldGroup:
    field: Field
    keys: tuple[int, ...]


class MultiMessageSystemVerilogGenerator(SystemVerilogGenerator):
    def generate(
        self,
        protocol: Protocol,
        stream: AxisStream,
        module_name: str | None = None,
    ) -> GeneratedFile:
        if not isinstance(protocol, MultiMessageProtocol):
            raise TypeError("MultiMessageSystemVerilogGenerator requires a MultiMessageProtocol")

        sub_proto = protocol.sub_protocol
        if isinstance(sub_proto, LengthPrefixedDiscriminatedSubProtocol):
            return self._generate_discriminated(protocol, stream, module_name, sub_proto)
        if not isinstance(sub_proto, LengthPrefixedProtocol):
            raise TypeError("MultiMessageProtocol SystemVerilog requires a LengthPrefixedProtocol or LengthPrefixedDiscriminatedSubProtocol sub_protocol")

        bus_bytes = stream.data_width // 8
        outer_total_length = protocol.total_length

        sub_total_length = sub_proto.total_length
        if sub_total_length <= 0:
            raise ValueError(f"{sub_proto.name}: sub-message header length must be positive")

        length_field = sub_proto.length_field
        scratch_count_width = counter_width((2 * bus_bytes) + 1)
        body_count_width = max(length_field.width, scratch_count_width)
        outer_layout = StreamLayout(stream, byte_offset=0)
        outer_parse_beats = (outer_total_length + bus_bytes - 1) // bus_bytes
        outer_tail_start = (outer_total_length - 1) % bus_bytes + 1

        outer_plan = GenerationPlan(
            protocol=protocol,
            stream=stream,
            layout=outer_layout,
            module_name=module_name or f"{protocol.name}_parser",
            parse_beats=outer_parse_beats,
        )
        outer_emitter = FieldExtractEmitter(outer_plan)

        # Determine if msg_count is captured on the final outer beat (needs comb bypass).
        outer_final_beat = outer_parse_beats - 1
        outer_final_beat_fields = {
            f.name
            for f in protocol.fields
            if any(b.beat == outer_final_beat for b in outer_layout.field_beats(f))
        }
        msg_count_field_name = protocol.message_count_field
        msg_count_signal = (
            f"{msg_count_field_name}_comb"
            if msg_count_field_name in outer_final_beat_fields
            else f"{msg_count_field_name}_reg"
        )

        sub_prefix = sv_identifier(sub_proto.name)
        sub_fields = list(sub_proto.fields)
        sub_field_declarations = self._emit_sub_field_declarations(sub_fields, sub_prefix)
        sub_comb_declarations = self._emit_sub_comb_declarations(sub_fields, sub_prefix)
        sub_field_reset_assignments = self._emit_sub_field_reset_assignments(sub_fields, sub_prefix)
        sub_field_capture_case_items = self._emit_sub_field_capture_case_items(sub_fields, sub_prefix)
        sub_comb_bypass_blocks = self._emit_sub_comb_bypass_blocks(sub_fields, sub_prefix)
        sub_output_assignments = self._emit_sub_output_assignments(sub_fields, sub_prefix)

        body = self.renderer.render(
            "multi_message_body.sv.j2",
            plan=outer_plan,
            bus_bytes=bus_bytes,
            outer_parse_beats=outer_parse_beats,
            outer_total_length=outer_total_length,
            outer_tail_start=outer_tail_start,
            sub_header_bytes=sub_total_length,
            outer_beat_count_width=counter_width(outer_parse_beats),
            sub_header_offset_width=counter_width(sub_total_length),
            scratch_count_width=scratch_count_width,
            body_count_width=body_count_width,
            msg_count_field_name=msg_count_field_name,
            msg_count_width=protocol.message_count_field_obj.width,
            msg_len_signal=f"{sub_prefix}_{length_field.name}_comb",
            msg_len_width=length_field.width,
            sub_prefix=sub_prefix,
            msg_count_signal=msg_count_signal,
            outer_field_declarations=outer_emitter.emit_declarations(),
            outer_comb_declarations=outer_emitter.emit_comb_declarations(),
            outer_comb_bypass_blocks=outer_emitter.emit_comb_bypass_blocks(),
            outer_field_reset_assignments=outer_emitter.emit_reset_assignments(),
            outer_field_capture_case_items=outer_emitter.emit_capture_case_items(),
            sub_field_declarations=sub_field_declarations,
            sub_comb_declarations=sub_comb_declarations,
            sub_field_reset_assignments=sub_field_reset_assignments,
            sub_field_capture_case_items=sub_field_capture_case_items,
            sub_comb_bypass_blocks=sub_comb_bypass_blocks,
            sub_output_assignments=sub_output_assignments,
        )

        extra_parsed_ports = [
            {"name": f"{sub_prefix}_{field.name}", "width": field.width}
            for field in sub_fields
        ]
        extra_status_ports = [
            {"name": f"{sub_prefix}_fields_valid"},
            {"name": f"{sub_prefix}_fields_fresh"},
        ]
        extra_counter_ports = [{"name": "malformed_count", "width": 32}]
        content = self.renderer.render(
            "module.sv.j2",
            plan=outer_plan,
            body=body,
            extra_parsed_ports=extra_parsed_ports,
            extra_status_ports=extra_status_ports,
            extra_counter_ports=extra_counter_ports,
        )
        return GeneratedFile(name=f"{outer_plan.module_name}.sv", content=content)

    def _generate_discriminated(
        self,
        protocol: MultiMessageProtocol,
        stream: AxisStream,
        module_name: str | None,
        sub_proto: LengthPrefixedDiscriminatedSubProtocol,
    ) -> GeneratedFile:
        itch_proto = sub_proto.discriminated
        bus_bytes = stream.data_width // 8
        outer_total_length = protocol.total_length
        outer_parse_beats = (outer_total_length + bus_bytes - 1) // bus_bytes
        outer_tail_start = (outer_total_length - 1) % bus_bytes + 1
        outer_layout = StreamLayout(stream, byte_offset=0)

        base_plan = self.build_plan(protocol, stream, module_name)
        outer_plan = GenerationPlan(
            protocol=protocol,
            stream=stream,
            layout=outer_layout,
            module_name=module_name or f"{protocol.name}_parser",
            parse_beats=outer_parse_beats,
            config_ports=base_plan.config_ports,
            drop_conditions=base_plan.drop_conditions,
        )
        outer_emitter = FieldExtractEmitter(outer_plan)

        config_reg_declarations = [
            f"logic [{p.width - 1}:0] {p.name}_reg;"
            for p in outer_plan.config_ports
        ]
        config_reg_reset_assignments = [
            f"{p.name}_reg <= {sv_int(p.width, p.default_value or 0)};"
            for p in outer_plan.config_ports
        ]
        config_reg_update_assignments = [
            f"{p.name}_reg <= {p.name};"
            for p in outer_plan.config_ports
        ]

        outer_final_beat = outer_parse_beats - 1
        outer_final_beat_fields = {
            f.name
            for f in protocol.fields
            if any(b.beat == outer_final_beat for b in outer_layout.field_beats(f))
        }
        msg_count_field_name = protocol.message_count_field
        msg_count_signal = (
            f"{msg_count_field_name}_comb"
            if msg_count_field_name in outer_final_beat_fields
            else f"{msg_count_field_name}_reg"
        )

        sub_total_length = sub_proto.total_length
        length_field = sub_proto.length_field
        sub_prefix = sv_identifier(sub_proto.name)
        sub_fields = list(sub_proto.fields)
        sub_field_declarations = self._emit_sub_field_declarations(sub_fields, sub_prefix)
        sub_comb_declarations = self._emit_sub_comb_declarations(sub_fields, sub_prefix)
        sub_field_reset_assignments = self._emit_sub_field_reset_assignments(sub_fields, sub_prefix)
        sub_field_capture_case_items = self._emit_sub_field_capture_case_items(sub_fields, sub_prefix)
        sub_comb_bypass_blocks = self._emit_sub_comb_bypass_blocks(sub_fields, sub_prefix)

        all_itch_fields = self._collect_all_itch_fields(itch_proto)
        itch_field_declarations = [
            f"logic [{f.width - 1}:0] {f.name}_reg;"
            for f in all_itch_fields
        ]
        itch_field_reset_assignments = [
            f"{f.name}_reg <= {f.width}'d0;"
            for f in all_itch_fields
        ]
        itch_output_assignments = [
            f"assign {f.name} = {f.name}_reg;"
            for f in all_itch_fields
        ]
        itch_byte_entries = self._build_itch_byte_entries(itch_proto)

        max_itch_length = max(itch_proto.variant_length.values())
        variant_lengths = tuple(
            (sv_int(itch_proto.discriminator.width, key), length)
            for key, length in sorted(itch_proto.variant_length.items())
        )

        scratch_count_width = counter_width((2 * bus_bytes) + 1)

        body = self.renderer.render(
            "multi_message_discriminated_body.sv.j2",
            plan=outer_plan,
            bus_bytes=bus_bytes,
            outer_parse_beats=outer_parse_beats,
            outer_total_length=outer_total_length,
            outer_tail_start=outer_tail_start,
            sub_header_bytes=sub_total_length,
            outer_beat_count_width=counter_width(outer_parse_beats),
            sub_header_offset_width=counter_width(sub_total_length),
            scratch_count_width=scratch_count_width,
            msg_count_width=protocol.message_count_field_obj.width,
            msg_len_signal=f"{sub_prefix}_{length_field.name}_comb",
            msg_len_width=length_field.width,
            msg_count_signal=msg_count_signal,
            outer_field_declarations=outer_emitter.emit_declarations(),
            outer_comb_declarations=outer_emitter.emit_comb_declarations(),
            outer_comb_bypass_blocks=outer_emitter.emit_comb_bypass_blocks(),
            outer_field_reset_assignments=outer_emitter.emit_reset_assignments(),
            outer_field_capture_case_items=outer_emitter.emit_capture_case_items(),
            sub_field_declarations=sub_field_declarations,
            sub_comb_declarations=sub_comb_declarations,
            sub_field_reset_assignments=sub_field_reset_assignments,
            sub_field_capture_case_items=sub_field_capture_case_items,
            sub_comb_bypass_blocks=sub_comb_bypass_blocks,
            config_reg_declarations=config_reg_declarations,
            config_reg_reset_assignments=config_reg_reset_assignments,
            config_reg_update_assignments=config_reg_update_assignments,
            itch_field_declarations=itch_field_declarations,
            itch_field_reset_assignments=itch_field_reset_assignments,
            itch_output_assignments=itch_output_assignments,
            itch_byte_entries=itch_byte_entries,
            variant_lengths=variant_lengths,
            discriminator_name=itch_proto.discriminator.name,
            sub_parse_offset_width=counter_width(max_itch_length),
        )

        itch_parsed_ports = [{"name": f.name, "width": f.width} for f in all_itch_fields]
        itch_status_ports = [
            {"name": "itch_fields_valid"},
            {"name": "itch_fields_fresh"},
        ]

        content = self.renderer.render(
            "module.sv.j2",
            plan=outer_plan,
            body=body,
            forward=False,
            extra_parsed_ports=itch_parsed_ports,
            extra_status_ports=itch_status_ports,
            extra_counter_ports=[{"name": "malformed_count", "width": 32}],
        )
        return GeneratedFile(name=f"{outer_plan.module_name}.sv", content=content)

    @staticmethod
    def _collect_all_itch_fields(proto: DiscriminatedProtocol) -> list[Field]:
        all_fields = list(proto.fields)
        fields_by_name = {f.name: f for f in all_fields}
        for variant_fields in proto.variants.values():
            for f in variant_fields:
                if f.name not in fields_by_name:
                    all_fields.append(f)
                    fields_by_name[f.name] = f
                elif fields_by_name[f.name].width != f.width:
                    raise ValueError(
                        f"{proto.name}: field '{f.name}' has multiple widths"
                    )
        return all_fields

    def _build_itch_byte_entries(self, proto: DiscriminatedProtocol) -> list[_ItchByteEntry]:
        common_names = {f.name for f in proto.fields}
        name_locations: dict[str, set[tuple[int, int]]] = {}
        variant_groups: dict[tuple[str, int, int], _VariantFieldGroup] = {}

        common_by_offset: dict[int, list[str]] = {}
        for field in proto.fields:
            name_locations.setdefault(field.name, set()).add((field.offset, field.width))
            for header_byte, field_hi, field_lo, source_hi in self._field_byte_slices(field):
                assignment = (
                    f"{field.name}_reg[{field_hi}:{field_lo}] <= scratch_byte_comb[{source_hi}:0];"
                )
                common_by_offset.setdefault(header_byte, []).append(assignment)

        for key, vfields in proto.variants.items():
            for f in vfields:
                if f.name in common_names:
                    continue
                name_locations.setdefault(f.name, set()).add((f.offset, f.width))
                group_key = (f.name, f.offset, f.width)
                existing = variant_groups.get(group_key)
                if existing is None:
                    variant_groups[group_key] = _VariantFieldGroup(field=f, keys=(key,))
                else:
                    variant_groups[group_key] = _VariantFieldGroup(
                        field=existing.field,
                        keys=tuple(sorted(existing.keys + (key,))),
                    )

        variant_by_offset: dict[int, dict[int, list[str]]] = {}
        for group in variant_groups.values():
            locations = name_locations[group.field.name]
            for header_byte, field_hi, field_lo, source_hi in self._field_byte_slices(group.field):
                assignment = (
                    f"{group.field.name}_reg[{field_hi}:{field_lo}] <= scratch_byte_comb[{source_hi}:0];"
                )
                if len(locations) == 1:
                    common_by_offset.setdefault(header_byte, []).append(assignment)
                else:
                    for key in group.keys:
                        variant_by_offset.setdefault(header_byte, {}).setdefault(key, []).append(assignment)

        all_offsets = sorted(set(list(common_by_offset) + list(variant_by_offset)))
        entries: list[_ItchByteEntry] = []
        for offset in all_offsets:
            common = tuple(common_by_offset.get(offset, []))

            asgn_to_keys: dict[tuple[str, ...], list[int]] = {}
            for key, assignments in sorted(variant_by_offset.get(offset, {}).items()):
                asgn_to_keys.setdefault(tuple(assignments), []).append(key)

            variant_entries = tuple(
                _VariantByteEntry(
                    key_literals=tuple(sv_int(proto.discriminator.width, k) for k in sorted(keys)),
                    assignments=tuple(assignments),
                )
                for assignments, keys in sorted(asgn_to_keys.items())
            )
            entries.append(_ItchByteEntry(offset=offset, common=common, variant_entries=variant_entries))

        return entries

    def _field_byte_slices(self, field) -> list[tuple[int, int, int, int]]:
        """Return (header_byte, field_hi, field_lo, source_hi) for each byte of field."""
        slices: list[tuple[int, int, int, int]] = []
        for field_byte in range(field.width_bytes):
            header_byte = field.offset + field_byte
            bits_this_byte = min(8, field.width - field_byte * 8)
            field_hi = field.width - field_byte * 8 - 1
            field_lo = max(0, field_hi - bits_this_byte + 1)
            slices.append((header_byte, field_hi, field_lo, bits_this_byte - 1))
        return slices

    def _emit_sub_field_declarations(self, fields, prefix: str) -> list[str]:
        return [
            f"logic [{field.width - 1}:0] {prefix}_{field.name}_reg;"
            for field in fields
        ]

    def _emit_sub_comb_declarations(self, fields, prefix: str) -> list[str]:
        return [
            f"logic [{field.width - 1}:0] {prefix}_{field.name}_comb;"
            for field in fields
        ]

    def _emit_sub_field_reset_assignments(self, fields, prefix: str) -> list[str]:
        return [
            f"{prefix}_{field.name}_reg <= {field.width}'d0;"
            for field in fields
        ]

    def _emit_sub_field_capture_case_items(self, fields, prefix: str) -> list[str]:
        assignments_by_byte: dict[int, list[str]] = {}
        for field in fields:
            for header_byte, field_hi, field_lo, source_hi in self._field_byte_slices(field):
                assignments_by_byte.setdefault(header_byte, []).append(
                    f"{prefix}_{field.name}_reg[{field_hi}:{field_lo}] <= scratch_byte_comb[{source_hi}:0];"
                )

        lines: list[str] = []
        for header_byte, assignments in sorted(assignments_by_byte.items()):
            lines.append(f"              {header_byte}: begin")
            for assignment in assignments:
                lines.append(f"                {assignment}")
            lines.append("              end")
        return lines

    def _emit_sub_comb_bypass_blocks(self, fields, prefix: str) -> list[str]:
        blocks: list[str] = []
        for field in fields:
            lines = [
                "always_comb begin",
                f"  {prefix}_{field.name}_comb = {prefix}_{field.name}_reg;",
                "  case (sub_header_offset_reg)",
            ]
            for header_byte, field_hi, field_lo, source_hi in self._field_byte_slices(field):
                lines.append(
                    f"    {header_byte}: {prefix}_{field.name}_comb[{field_hi}:{field_lo}] = scratch_byte_comb[{source_hi}:0];"
                )
            lines += ["    default: ;", "  endcase", "end"]
            blocks.append("\n".join(lines))
        return blocks

    def _emit_sub_output_assignments(self, fields, prefix: str) -> list[str]:
        return [
            f"assign {prefix}_{field.name} = {prefix}_{field.name}_reg;"
            for field in fields
        ]
