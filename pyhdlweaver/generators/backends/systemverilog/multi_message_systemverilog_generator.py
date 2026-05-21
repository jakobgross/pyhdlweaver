from pyhdlweaver.generators.generated_file import GeneratedFile
from pyhdlweaver.generators.backends.systemverilog.field_extract_emitter import FieldExtractEmitter
from pyhdlweaver.generators.backends.systemverilog.generation_plan import GenerationPlan
from pyhdlweaver.generators.backends.systemverilog.systemverilog_generator import SystemVerilogGenerator
from pyhdlweaver.generators.backends.systemverilog.utils import counter_width, sv_identifier
from pyhdlweaver.protocols import Protocol
from pyhdlweaver.protocols.length_prefixed_protocol import LengthPrefixedProtocol
from pyhdlweaver.protocols.multi_message_protocol import MultiMessageProtocol
from pyhdlweaver.protocols.definitions import StreamLayout
from pyhdlweaver.stream.axi_stream import AxisStream


class MultiMessageSystemVerilogGenerator(SystemVerilogGenerator):
    def generate(
        self,
        protocol: Protocol,
        stream: AxisStream,
        module_name: str | None = None,
    ) -> GeneratedFile:
        if not isinstance(protocol, MultiMessageProtocol):
            raise TypeError("MultiMessageSystemVerilogGenerator requires a MultiMessageProtocol")

        bus_bytes = stream.data_width // 8
        outer_total_length = protocol.total_length
        sub_proto = protocol.sub_protocol
        if not isinstance(sub_proto, LengthPrefixedProtocol):
            raise TypeError("MultiMessageProtocol SystemVerilog currently requires a LengthPrefixedProtocol sub_protocol")

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
