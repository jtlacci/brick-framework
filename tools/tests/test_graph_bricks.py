"""Focused tests for the generated brick diagram."""

from __future__ import annotations

import unittest

from tools import graph_bricks


class GraphTests(unittest.TestCase):
    def test_nodes_are_explicitly_bricks_and_show_lanes(self) -> None:
        diagram = graph_bricks.render(
            {
                "flow": ({"store": "orchestrated"}, (), "workflow"),
                "store": ({}, ("sqlite:data",), "strict"),
            }
        )
        self.assertIn("BRICK: flow<br/>lane: workflow", diagram)
        self.assertIn("BRICK: store<br/>lane: strict<br/>sqlite:data", diagram)
        self.assertIn("class flow workflow", diagram)
        self.assertIn("flow --> store", diagram)


if __name__ == "__main__":
    unittest.main()
