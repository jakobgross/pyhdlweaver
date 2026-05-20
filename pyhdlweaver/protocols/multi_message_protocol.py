from dataclasses import dataclass

from pyhdlweaver.protocols.definitions.field import Field
from pyhdlweaver.protocols.fixed_protocol import FixedProtocol
from pyhdlweaver.protocols.length_prefixed_protocol import LengthPrefixedProtocol


@dataclass(frozen=True, kw_only=True)
class MultiMessageProtocol(FixedProtocol):
    """Fixed outer header contains a count field, followed by N length-prefixed sub-messages.

    The outer header is parsed once per input frame. Then for each of the N sub-messages,
    a 2-step process reads the sub-header (length field) and forwards the message payload
    as a separate output AXI-Stream frame.
    """

    message_count_field: str
    sub_protocol: LengthPrefixedProtocol

    @property
    def protocol_kind(self) -> str:
        return "multi_message"

    @property
    def is_fixed_length(self) -> bool:
        return False

    def __post_init__(self) -> None:
        super().__post_init__()
        if not any(f.name == self.message_count_field for f in self.fields):
            raise ValueError(
                f"{self.name}: message_count_field '{self.message_count_field}' must be in fields"
            )

    @property
    def message_count_field_obj(self) -> Field:
        return next(f for f in self.fields if f.name == self.message_count_field)
