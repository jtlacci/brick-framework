"""Deliberately invalid connections used to prove the type gate is active."""

from bricks.example_brick import run as run_example_brick
from bricks.example_brick.contract import BrickInput, BrickOutput
from workflows.example_workflow.contract import WorkflowInput


def pass_workflow_contract_directly(inputs: WorkflowInput) -> BrickOutput:
    """A workflow boundary may not masquerade as a brick boundary."""
    return run_example_brick(inputs)


def construct_brick_input_from_untyped_scalar(value: int) -> BrickInput:
    """Plain scalars may not bypass the brick's semantic field type."""
    return {"value": value}
