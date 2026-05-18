from dataclasses import dataclass, field
from typing import Mapping, Sequence

from pyhdlweaver.actions.action import Action


def _validate_destination(destination: str | None, label: str = "destination") -> None:
    if destination == "":
        raise ValueError(f"{label} must be non-empty")


def _validate_register(register: str, label: str = "register") -> None:
    if not register:
        raise ValueError(f"{label} must be non-empty")


def _validate_default_value(value: int | None, label: str = "default_value") -> None:
    if value is not None and value < 0:
        raise ValueError(f"{label} must be non-negative")


@dataclass(frozen=True, kw_only=True)
class RouteAction(Action):
    """Base class for actions that select downstream consumers."""

    @property
    def action_kind(self) -> str:
        return "route"


@dataclass(frozen=True, kw_only=True)
class RouteByValue(RouteAction):
    """Route by exact field value."""

    table: Mapping[int, str] = field(default_factory=dict)
    default: str | None = None

    def __post_init__(self) -> None:
        if not self.table and self.default is None:
            raise ValueError("table or default route is required")
        for value, destination in self.table.items():
            if value < 0:
                raise ValueError("route values must be non-negative")
            _validate_destination(destination, "route destination")
        _validate_destination(self.default, "default route")
        object.__setattr__(self, "table", dict(self.table))


@dataclass(frozen=True, kw_only=True)
class RouteByRange(RouteAction):
    """Route by inclusive field-value ranges."""

    ranges: Sequence[tuple[int, int, str]] = field(default_factory=tuple)
    default: str | None = None

    def __post_init__(self) -> None:
        if not self.ranges and self.default is None:
            raise ValueError("ranges or default route is required")

        ranges = tuple(self.ranges)
        for min_value, max_value, destination in ranges:
            if min_value < 0:
                raise ValueError("range min values must be non-negative")
            if max_value < min_value:
                raise ValueError("range max values must be greater than or equal to min")
            _validate_destination(destination, "route destination")
        _validate_destination(self.default, "default route")
        object.__setattr__(self, "ranges", ranges)


@dataclass(frozen=True, kw_only=True)
class RouteToAll(RouteAction):
    """Broadcast to every listed consumer."""

    consumers: Sequence[str]

    def __post_init__(self) -> None:
        consumers = tuple(self.consumers)
        if not consumers:
            raise ValueError("at least one consumer is required")
        if any(not consumer for consumer in consumers):
            raise ValueError("consumers must be non-empty")
        object.__setattr__(self, "consumers", consumers)


@dataclass(frozen=True, kw_only=True)
class RouteByRegister(RouteAction):
    """Route to destination when field value matches a configured register value."""

    register: str
    destination: str
    default: str | None = None
    default_value: int | None = None
    mask: int | None = None

    def __post_init__(self) -> None:
        _validate_register(self.register)
        _validate_destination(self.destination)
        _validate_destination(self.default, "default route")
        _validate_default_value(self.default_value)
        if self.mask is not None and self.mask < 0:
            raise ValueError("mask must be non-negative")


@dataclass(frozen=True, kw_only=True)
class RouteByRegistersRange(RouteAction):
    """Route to destination when field value is within a configured register range."""

    min_register: str
    max_register: str
    destination: str
    default: str | None = None
    min_default: int | None = None
    max_default: int | None = None

    def __post_init__(self) -> None:
        _validate_register(self.min_register, "min_register")
        _validate_register(self.max_register, "max_register")
        _validate_destination(self.destination)
        _validate_destination(self.default, "default route")
        _validate_default_value(self.min_default, "min_default")
        _validate_default_value(self.max_default, "max_default")
        if (
            self.min_default is not None
            and self.max_default is not None
            and self.max_default < self.min_default
        ):
            raise ValueError("max_default must be greater than or equal to min_default")
