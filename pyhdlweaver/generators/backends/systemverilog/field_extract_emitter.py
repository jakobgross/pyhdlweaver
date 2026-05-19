from dataclasses import dataclass

from pyhdlweaver.generators.backends.systemverilog.generation_plan import GenerationPlan


@dataclass(frozen=True)
class FieldExtractEmitter:
    plan: GenerationPlan

    def emit_declarations(self) -> list[str]:
        return [
            f"logic [{field.width - 1}:0] {field.name}_reg;"
            for field in self.plan.protocol.fields
        ]

    def emit_reset_assignments(self) -> list[str]:
        return [
            f"{field.name}_reg <= {field.width}'d0;"
            for field in self.plan.protocol.fields
        ]

    def emit_capture_case_items(self) -> list[str]:
        assignments_by_beat: dict[int, list[str]] = {}
        for field in self.plan.protocol.fields:
            for beat in self.plan.layout.field_beats(field):
                for byte_in_beat in range(beat.byte_lo, beat.byte_hi + 1):
                    protocol_byte = (
                        beat.beat * self.plan.layout.layout.bus_width_bytes
                        + byte_in_beat
                        - self.plan.layout.layout.byte_offset
                    )
                    field_byte = protocol_byte - field.offset
                    bits_this_byte = min(8, field.width - field_byte * 8)
                    field_hi = field.width - (field_byte * 8) - 1
                    field_lo = max(0, field_hi - bits_this_byte + 1)
                    bit_lo = byte_in_beat * 8
                    bit_hi = bit_lo + bits_this_byte - 1
                    assignments_by_beat.setdefault(beat.beat, []).append(
                        f"{field.name}_reg[{field_hi}:{field_lo}] <= s_axis_tdata[{bit_hi}:{bit_lo}];"
                    )

        lines: list[str] = []
        for beat, assignments in sorted(assignments_by_beat.items()):
            lines.append(f"            {beat}: begin")
            for assignment in assignments:
                lines.append(f"              {assignment}")
            lines.append("            end")
        return lines
