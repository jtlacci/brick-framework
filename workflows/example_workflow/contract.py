"""Typed boundary and architecture facts for the example workflow."""

from typing import NewType, TypedDict


CONTRACT_VERSION = 1
BRICK_DEPENDENCIES: tuple[str, ...] = ("example_brick",)


# Workflow boundary values are intentionally distinct from brick values.
# flow.py owns the explicit translation between the two contracts.
WorkflowValue = NewType("WorkflowValue", int)


class WorkflowInput(TypedDict):
    """Input accepted by the workflow's run()."""

    value: WorkflowValue


class WorkflowOutput(TypedDict):
    """Output returned by the workflow's run()."""

    value: WorkflowValue
