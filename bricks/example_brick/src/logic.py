"""Replace with brick logic. Route external calls through input adapters."""

from ..contract import BrickInput, BrickOutput


def execute(inputs: BrickInput, run_context: dict) -> BrickOutput:
    """Execute the brick's domain logic."""
    raise NotImplementedError
