from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigPort:
    name: str
    width: int
