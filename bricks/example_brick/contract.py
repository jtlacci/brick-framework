"""Typed boundary and architecture facts for the example brick."""

from typing import TypedDict


CONTRACT_VERSION = 1
LANE = "strict"
SIBLING_DEPENDENCIES: dict[str, str] = {}
OWNED_STATE: tuple[str, ...] = ()


class BrickInput(TypedDict):
    """Input accepted by run(). Replace with domain fields."""

    value: int


class BrickOutput(TypedDict):
    """Output returned by run(). Replace with domain fields."""

    value: int
