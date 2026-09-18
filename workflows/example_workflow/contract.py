"""Typed boundary and architecture facts for the example workflow."""

from typing import TypedDict


CONTRACT_VERSION = 1
BRICK_DEPENDENCIES: tuple[str, ...] = ("example_brick",)


class WorkflowInput(TypedDict):
    """Input accepted by the workflow's run()."""

    value: int


class WorkflowOutput(TypedDict):
    """Output returned by the workflow's run()."""

    value: int
