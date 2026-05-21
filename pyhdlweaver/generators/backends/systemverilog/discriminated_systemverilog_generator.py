from dataclasses import dataclass

from pyhdlweaver.generators.generated_file import GeneratedFile
from pyhdlweaver.generators.backends.systemverilog.field_extract_emitter import FieldExtractEmitter
from pyhdlweaver.generators.backends.systemverilog.generation_plan import GenerationPlan
from pyhdlweaver.generators.backends.systemverilog.systemverilog_generator import SystemVerilogGenerator
from pyhdlweaver.generators.backends.systemverilog.utils import counter_width, sv_int
from pyhdlweaver.protocols import Protocol
from pyhdlweaver.protocols.definitions import StreamLayout
from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols.discriminated_protocol import DiscriminatedProtocol
from pyhdlweaver.protocols.fixed_protocol import FixedProtocol
from pyhdlweaver.stream.axi_stream import AxisStream


@dataclass(frozen=True)
class _VariantEntry:
    key_literals: tuple[str, ...]
    assignments: tuple[str, ...]


@dataclass(frozen=True)
class _BeatEntry:
    beat: int
    common: tuple[str, ...]
    variants: tuple[_VariantEntry, ...]


@dataclass(frozen=True)
class _VariantFieldGroup:
    field: Field
    keys: tuple[int, ...]


class DiscriminatedSystemVerilogGenerator(SystemVerilogGenerator):
    """SV generator for DiscriminatedProtocol: variant-conditional field capture."""

    def generate(
        self,
        protocol: Protocol,
        stream: AxisStream,
        module_name: str | None = None,
    ) -> GeneratedFile:
        if not isinstance(protocol, DiscriminatedProtocol):
            raise TypeError("DiscriminatedSystemVerilogGenerator requires a DiscriminatedProtocol")

        all_fields = self._collect_all_fields(protocol)
        max_length = max(protocol.variant_length.values())
        bus_bytes = stream.data_width // 8
        parse_beats = (max_length + bus_bytes - 1) // bus_bytes

        # Virtual protocol includes every output field.
        virtual_protocol = FixedProtocol(
            name=protocol.name,
            fields=all_fields,
            total_length=max_length,
        )

        layout = StreamLayout(stream, byte_offset=0)
        plan = GenerationPlan(
            protocol=virtual_protocol,
            stream=stream,
            layout=layout,
            module_name=module_name or f"{protocol.name}_parser",
            parse_beats=parse_beats,
        )

        emitter = FieldExtractEmitter(plan)
        beat_entries = self._build_beat_entries(protocol, layout)
        discriminator_beat, discriminator_current_expr = _field_expr(protocol.discriminator, layout)
        variant_lengths = tuple(
            (sv_int(protocol.discriminator.width, key), length)
            for key, length in sorted(protocol.variant_length.items())
        )

        body = self.renderer.render(
            "discriminated_body.sv.j2",
            plan=plan,
            parse_beats=parse_beats,
            beat_count_width=counter_width(parse_beats),
            length_count_width=counter_width(max_length + bus_bytes + 1),
            field_declarations=emitter.emit_declarations(),
            field_reset_assignments=emitter.emit_reset_assignments(),
            beat_entries=beat_entries,
            discriminator_name=protocol.discriminator.name,
            discriminator_width=protocol.discriminator.width,
            discriminator_beat=discriminator_beat,
            discriminator_current_expr=discriminator_current_expr,
            variant_lengths=variant_lengths,
            forward=protocol.forward,
        )

        content = self.renderer.render(
            "module.sv.j2",
            plan=plan,
            body=body,
            forward=protocol.forward,
            extra_counter_ports=[{"name": "malformed_count", "width": 32}],
        )
        return GeneratedFile(name=f"{plan.module_name}.sv", content=content)

    def _build_beat_entries(
        self,
        protocol: DiscriminatedProtocol,
        layout: StreamLayout,
    ) -> list[_BeatEntry]:
        common_names = {f.name for f in protocol.fields}
        name_locations: dict[str, set[tuple[int, int]]] = {}
        variant_groups: dict[tuple[str, int, int], _VariantFieldGroup] = {}

        for field in protocol.fields:
            name_locations.setdefault(field.name, set()).add((field.offset, field.width))

        for key, vfields in protocol.variants.items():
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

        # Common captures by beat.
        common_by_beat: dict[int, list[str]] = {}
        for field in protocol.fields:
            for assignment, beat in _field_assignments(field, layout):
                common_by_beat.setdefault(beat, []).append(assignment)

        # Only same-name fields at different locations need discriminator branches.
        variant_by_beat: dict[int, dict[int, list[str]]] = {}
        for group in variant_groups.values():
            locations = name_locations[group.field.name]
            for assignment, beat in _field_assignments(group.field, layout):
                if len(locations) == 1:
                    common_by_beat.setdefault(beat, []).append(assignment)
                else:
                    for key in group.keys:
                        variant_by_beat.setdefault(beat, {}).setdefault(key, []).append(assignment)

        all_beats = sorted(set(list(common_by_beat) + list(variant_by_beat)))
        entries: list[_BeatEntry] = []
        for beat in all_beats:
            common = tuple(common_by_beat.get(beat, []))
            variants: list[_VariantEntry] = []
            assignments_to_keys: dict[tuple[str, ...], list[int]] = {}
            for key, assignments in sorted(variant_by_beat.get(beat, {}).items()):
                assignments_to_keys.setdefault(tuple(assignments), []).append(key)
            for assignments, keys in assignments_to_keys.items():
                key_literals = tuple(sv_int(protocol.discriminator.width, key) for key in keys)
                variants.append(_VariantEntry(
                    key_literals=key_literals,
                    assignments=assignments,
                ))
            entries.append(_BeatEntry(beat=beat, common=common, variants=tuple(variants)))
        return entries

    @staticmethod
    def _collect_all_fields(protocol: DiscriminatedProtocol) -> list[Field]:
        all_fields = list(protocol.fields)
        fields_by_name = {f.name: f for f in all_fields}
        for variant_fields in protocol.variants.values():
            for f in variant_fields:
                existing = fields_by_name.get(f.name)
                if existing is None:
                    all_fields.append(f)
                    fields_by_name[f.name] = f
                elif existing.width != f.width:
                    raise ValueError(
                        f"{protocol.name}: field '{f.name}' has multiple widths"
                    )
        return all_fields


def _field_assignments(field: Field, layout: StreamLayout) -> list[tuple[str, int]]:
    bus_bytes = layout.layout.bus_width_bytes
    byte_offset = layout.layout.byte_offset
    results: list[tuple[str, int]] = []
    for beat_info in layout.field_beats(field):
        beat = beat_info.beat
        for byte_in_beat in range(beat_info.byte_lo, beat_info.byte_hi + 1):
            protocol_byte = beat * bus_bytes + byte_in_beat - byte_offset
            field_byte = protocol_byte - field.offset
            bits_this_byte = min(8, field.width - field_byte * 8)
            field_hi = field.width - (field_byte * 8) - 1
            field_lo = max(0, field_hi - bits_this_byte + 1)
            bit_lo = byte_in_beat * 8
            bit_hi = bit_lo + bits_this_byte - 1
            assignment = (
                f"{field.name}_reg[{field_hi}:{field_lo}] <= s_axis_tdata[{bit_hi}:{bit_lo}];"
            )
            results.append((assignment, beat))
    return results


def _field_expr(field: Field, layout: StreamLayout) -> tuple[int, str]:
    """Return the beat and current-beat expression for a field that fits in one beat."""

    beats = layout.field_beats(field)
    if len(beats) != 1:
        raise NotImplementedError(
            "DiscriminatedProtocol discriminator fields must fit in one stream beat"
        )

    beat_info = beats[0]
    chunks: list[str] = []
    bus_bytes = layout.layout.bus_width_bytes
    byte_offset = layout.layout.byte_offset

    for byte_in_beat in range(beat_info.byte_lo, beat_info.byte_hi + 1):
        protocol_byte = beat_info.beat * bus_bytes + byte_in_beat - byte_offset
        field_byte = protocol_byte - field.offset
        bits_this_byte = min(8, field.width - field_byte * 8)
        bit_lo = byte_in_beat * 8
        bit_hi = bit_lo + bits_this_byte - 1
        chunks.append(f"s_axis_tdata[{bit_hi}:{bit_lo}]")

    if len(chunks) == 1:
        return beat_info.beat, chunks[0]
    return beat_info.beat, "{" + ", ".join(chunks) + "}"
