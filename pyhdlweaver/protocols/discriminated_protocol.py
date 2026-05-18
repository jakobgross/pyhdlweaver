from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from pyhdlweaver.data_packet import DataPacket
from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols.fixed_protocol import FixedProtocol
from pyhdlweaver.protocols.protocol import (
    _fields_tuple,
    _required_length,
)


@dataclass(frozen=True, kw_only=True)
class DiscriminatedProtocol(FixedProtocol):
    """A discriminator field selects one fixed-length variant."""

    discriminator: Field
    variants: Mapping[int, Sequence[Field]] = field(default_factory=dict)
    variant_length: Optional[Mapping[int, int]] = None

    @property
    def protocol_kind(self) -> str:
        return "discriminated"

    @property
    def parse_length(self) -> int:
        return _required_length(self.fields + (self.discriminator,))

    @property
    def is_fixed_length(self) -> bool:
        return True

    def length_for(self, discriminator_value: int) -> int:
        try:
            return self.variant_length[discriminator_value]  # type: ignore[index]
        except KeyError as exc:
            raise KeyError(
                f"{self.name}: unknown discriminator value {discriminator_value!r}"
            ) from exc

    def fields_for(self, discriminator_value: int) -> tuple[Field, ...]:
        try:
            return self.variants[discriminator_value]
        except KeyError as exc:
            raise KeyError(
                f"{self.name}: unknown discriminator value {discriminator_value!r}"
            ) from exc

    def eval(self, packet: DataPacket) -> dict[str, int | bytes]:
        values = super().eval(packet)
        discriminator_value = values[self.discriminator.name]
        if not isinstance(discriminator_value, int):
            raise TypeError(f"{self.name}: discriminator value must be an integer")
        for field_ in self.fields_for(discriminator_value):
            values[field_.name] = packet.read_field(field_)
        return values

    def __post_init__(self) -> None:
        common_fields = _fields_tuple(self.fields)

        if self.discriminator not in common_fields:
            common_fields = (self.discriminator,) + common_fields

        variants = {
            value: _fields_tuple(fields)
            for value, fields in self.variants.items()
        }
        if not variants:
            raise ValueError(f"{self.name}: at least one variant is required")

        if self.variant_length is None:
            variant_length = {
                value: _required_length(fields)
                for value, fields in variants.items()
            }
        else:
            variant_length = dict(self.variant_length)

        missing_lengths = set(variants) - set(variant_length)
        extra_lengths = set(variant_length) - set(variants)
        if missing_lengths or extra_lengths:
            raise ValueError(
                f"{self.name}: variant_length keys must match variants "
                f"(missing={sorted(missing_lengths)}, extra={sorted(extra_lengths)})"
            )

        for value, fields in variants.items():
            required_length = _required_length(fields + common_fields)
            if variant_length[value] < required_length:
                raise ValueError(
                    f"{self.name}: variant {value!r} length {variant_length[value]} "
                    f"does not cover fields ending at byte {required_length}"
                )

        lengths = set(variant_length.values())
        total_length = lengths.pop() if len(lengths) == 1 else None

        object.__setattr__(self, "fields", common_fields)
        object.__setattr__(self, "variants", variants)
        object.__setattr__(self, "variant_length", variant_length)
        object.__setattr__(self, "total_length", total_length)
