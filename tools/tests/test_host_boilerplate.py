"""Small host-language checks; business behavior remains intentionally absent."""

from __future__ import annotations

import unittest

from bricks.example_brick import run as run_brick
from workflows.example_workflow import run as run_workflow


class HostBoilerplateTests(unittest.TestCase):
    def test_brick_public_entry_is_an_unimplemented_placeholder(self) -> None:
        with self.assertRaises(NotImplementedError):
            run_brick({"value": 1})

    def test_workflow_composes_the_declared_brick_entry(self) -> None:
        with self.assertRaises(NotImplementedError):
            run_workflow({"value": 1})


if __name__ == "__main__":
    unittest.main()
