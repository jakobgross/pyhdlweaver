from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedFile:
    name: str
    content: str
