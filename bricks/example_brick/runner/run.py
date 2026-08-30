"""The brick's repository-internal entry point."""

from ..contract import BrickInput, BrickOutput


def run(
    inputs: BrickInput, *, fresh: bool = False, save: bool = False
) -> BrickOutput:
    """Run the brick and return its output.

    ``fresh`` performs this brick's external calls without changing tracked
    examples. ``save`` implies fresh and replaces reviewed tracked examples.
    Neither option is forwarded to sibling bricks.
    """
    raise NotImplementedError
