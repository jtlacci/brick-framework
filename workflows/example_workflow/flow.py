"""Composition skeleton for the example workflow."""

from bricks.example_brick import run as run_example_brick
from bricks.example_brick.contract import BrickInput, BrickOutput, BrickValue

from .contract import WorkflowInput, WorkflowOutput, WorkflowValue


def to_brick_input(inputs: WorkflowInput) -> BrickInput:
    """Translate the workflow boundary into the brick's public contract."""
    return {"value": BrickValue(inputs["value"])}


def from_brick_output(output: BrickOutput) -> WorkflowOutput:
    """Translate the brick result back into the workflow's public contract."""
    return {"value": WorkflowValue(output["value"])}


def run(inputs: WorkflowInput) -> WorkflowOutput:
    """Compose declared brick entry points without owning external effects."""
    return from_brick_output(run_example_brick(to_brick_input(inputs)))
