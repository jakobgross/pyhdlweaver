from dataclasses import dataclass

from pyhdlweaver.actions.action import Action


def _validate_register(register: str, label: str = "register") -> None:
    if not register:
        raise ValueError(f"{label} must be non-empty")


def _validate_default_value(value: int | None, label: str = "default_value") -> None:
    if value is not None and value < 0:
        raise ValueError(f"{label} must be non-negative")


@dataclass(frozen=True, kw_only=True)
class DropAction(Action):
    """Base class for validation actions that drop packets and increment counters."""

    counter: str | None = None

    @property
    def action_kind(self) -> str:
        return "drop"

    @property
    def drop_reason(self) -> str:
        return self.__class__.__name__

    def counter_name(self, field_name: str) -> str:
        if self.counter is not None:
            return self.counter
        return f"{field_name}_{self.drop_reason}_count"


@dataclass(frozen=True, kw_only=True)
class DropOnMismatch(DropAction):
    """Drop when a field value does not match expected after applying mask."""

    expected: int
    mask: int | None = None

    @property
    def drop_reason(self) -> str:
        return "mismatch"

    def __post_init__(self) -> None:
        if self.expected < 0:
            raise ValueError("expected must be non-negative")
        if self.mask is not None and self.mask < 0:
            raise ValueError("mask must be non-negative")


@dataclass(frozen=True, kw_only=True)
class DropOnFlag(DropAction):
    """Drop when any bit selected by mask is set."""

    mask: int

    @property
    def drop_reason(self) -> str:
        return "flag"

    def __post_init__(self) -> None:
        if self.mask <= 0:
            raise ValueError("mask must be positive")


@dataclass(frozen=True, kw_only=True)
class DropOnRange(DropAction):
    """Drop when a field value is outside inclusive min/max bounds."""

    min_value: int
    max_value: int

    @property
    def drop_reason(self) -> str:
        return "range"

    def __post_init__(self) -> None:
        if self.min_value < 0:
            raise ValueError("min_value must be non-negative")
        if self.max_value < self.min_value:
            raise ValueError("max_value must be greater than or equal to min_value")


@dataclass(frozen=True, kw_only=True)
class DropOnRegisterMatch(DropAction):
    """Drop when a field value matches a configured register value."""

    register: str
    default_value: int | None = None
    mask: int | None = None

    @property
    def drop_reason(self) -> str:
        return "register_match"

    def __post_init__(self) -> None:
        _validate_register(self.register)
        _validate_default_value(self.default_value)
        if self.mask is not None and self.mask < 0:
            raise ValueError("mask must be non-negative")


@dataclass(frozen=True, kw_only=True)
class DropOnRegisterMismatch(DropAction):
    """Drop when a field value does not match a configured register value."""

    register: str
    default_value: int | None = None
    mask: int | None = None

    @property
    def drop_reason(self) -> str:
        return "register_mismatch"

    def __post_init__(self) -> None:
        _validate_register(self.register)
        _validate_default_value(self.default_value)
        if self.mask is not None and self.mask < 0:
            raise ValueError("mask must be non-negative")


@dataclass(frozen=True, kw_only=True)
class DropOnRegisterFlagMismatch(DropAction):
    """Drop when selected field flag bits differ from a configured register value."""

    register: str
    default_value: int | None = None
    mask: int

    @property
    def drop_reason(self) -> str:
        return "register_flag_mismatch"

    def __post_init__(self) -> None:
        _validate_register(self.register)
        _validate_default_value(self.default_value)
        if self.mask <= 0:
            raise ValueError("mask must be positive")


@dataclass(frozen=True, kw_only=True)
class DropOnRegisterRange(DropAction):
    """Drop when a field value is outside a configured inclusive register range."""

    min_register: str
    max_register: str
    min_default: int | None = None
    max_default: int | None = None

    @property
    def drop_reason(self) -> str:
        return "register_range"

    def __post_init__(self) -> None:
        _validate_register(self.min_register, "min_register")
        _validate_register(self.max_register, "max_register")
        _validate_default_value(self.min_default, "min_default")
        _validate_default_value(self.max_default, "max_default")
        if (
            self.min_default is not None
            and self.max_default is not None
            and self.max_default < self.min_default
        ):
            raise ValueError("max_default must be greater than or equal to min_default")
