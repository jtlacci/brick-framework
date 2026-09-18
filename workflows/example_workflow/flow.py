"""Composition skeleton for the example workflow."""

from bricks.example_brick import run as run_example_brick

from .contract import WorkflowInput, WorkflowOutput


def run(inputs: WorkflowInput) -> WorkflowOutput:
    """Compose declared brick entry points without owning external effects."""
    return run_example_brick(inputs)
