from dataclasses import dataclass, field, replace
import math
from typing import Sequence

from pyhdlweaver.actions import Action, DropAction


@dataclass(frozen=True)
class Field:
    """A named field at a fixed byte offset within a protocol header."""

    name: str
    offset: int  # bytes from start of protocol layer
    width: int  # bits
    actions: Sequence[Action] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("field offset must be non-negative")
        if self.width <= 0:
            raise ValueError("field width must be positive")
        if any(not isinstance(action, Action) for action in self.actions):
            raise TypeError("field actions must be Action instances")
        object.__setattr__(self, "actions", tuple(self.actions))

    @property
    def width_bytes(self) -> int:
        return math.ceil(self.width / 8)

    @property
    def end_offset(self) -> int:
        return self.offset + self.width_bytes

    @property
    def drop_counter_names(self) -> tuple[str, ...]:
        return tuple(
            action.counter_name(self.name)
            for action in self.actions
            if isinstance(action, DropAction)
        )

    def with_actions(self, *actions: Action) -> "Field":
        return replace(self, actions=self.actions + tuple(actions))

    def __repr__(self):
        return f"Field({self.name!r}, offset={self.offset}, width={self.width}b / {self.width_bytes}B)"
