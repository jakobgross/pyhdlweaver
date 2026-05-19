from dataclasses import dataclass


@dataclass(frozen=True)
class RouteCondition:
    expression: str
    destination: int
    destination_literal: str
