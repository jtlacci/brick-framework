"""Typed boundary and architecture facts for the example brick."""

from typing import NewType, TypedDict


CONTRACT_VERSION = 1
LANE = "strict"
SIBLING_DEPENDENCIES: dict[str, str] = {}
OWNED_STATE: tuple[str, ...] = ()


# Replace this placeholder with a domain name such as CustomerId or UsdCents.
# A distinct boundary type prevents accidental structural wiring.
BrickValue = NewType("BrickValue", int)


class BrickInput(TypedDict):
    """Input accepted by run(). Replace with domain fields."""

    value: BrickValue


class BrickOutput(TypedDict):
    """Output returned by run(). Replace with domain fields."""

    value: BrickValue
