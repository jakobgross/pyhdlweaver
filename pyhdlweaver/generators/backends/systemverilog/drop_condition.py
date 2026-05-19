from dataclasses import dataclass


@dataclass(frozen=True)
class DropCondition:
    expression: str
    counter_name: str
