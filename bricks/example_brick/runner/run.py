"""The example brick's repository-internal entry point."""

from ..contract import BrickInput, BrickOutput
from ..src.logic import execute


def run(inputs: BrickInput) -> BrickOutput:
    """Run the brick. Domain implementations replace the example stub."""
    return execute(inputs)
