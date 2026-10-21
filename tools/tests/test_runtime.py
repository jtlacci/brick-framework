"""Tests for bricks/_runtime.py and bricks/_yaml.py."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bricks import _runtime, _yaml  # noqa: E402


def fake_contract(name: str, deterministic: bool) -> None:
    module = types.ModuleType(f"bricks.{name}.contract")
    module.DETERMINISTIC = deterministic
    sys.modules[f"bricks.{name}.contract"] = module
    _runtime.is_deterministic.cache_clear()


class YamlTests(unittest.TestCase):
    def test_subset(self) -> None:
        text = (
            "a: 1  # comment\n"
            "b:\n  c: [x, 'y z', 3.5]\n  d: {k: true, n: null}\n"
            "e:\n  - one\n  - \"two # not a comment\"\n"
        )
        self.assertEqual(_yaml.loads(text), {
            "a": 1, "b": {"c": ["x", "y z", 3.5], "d": {"k": True, "n": None}},
            "e": ["one", "two # not a comment"],
        })

    def test_rejects_nested_flow(self) -> None:
        with self.assertRaises(_yaml.YamlError):
            _yaml.loads("a: [1, [2]]\n")

    def test_rejects_duplicate_keys(self) -> None:
        with self.assertRaises(_yaml.YamlError):
            _yaml.loads("a: 1\na: 2\n")


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spool = tempfile.mkdtemp(prefix="brick-spool-")
        patch = mock.patch.dict(os.environ, {_runtime.CAPTURE_ENV: self.spool, _runtime.TREES_ENV: "{}"})
        patch.start()
        self.addCleanup(patch.stop)
        fake_contract("det", True)
        fake_contract("model", False)

    def records(self) -> list[dict]:
        out = []
        for path in sorted(Path(self.spool).glob("*.jsonl")):
            out += [json.loads(line) for line in path.read_text().splitlines()]
        return out

    def test_deterministic_run_keeps_only_the_output_hash(self) -> None:
        output = _runtime.run_brick("det", {"x": 1}, lambda inputs, ctx: {"y": inputs["x"] + 1})
        self.assertEqual(output, {"y": 2})
        [record] = self.records()
        self.assertEqual(record["kind"], "run")
        self.assertEqual(record["input"], {"x": 1})
        self.assertEqual(record["output_hash"], _runtime.digest({"y": 2}))
        self.assertNotIn("output", record)

    def test_nondeterministic_run_keeps_the_output(self) -> None:
        _runtime.run_brick("model", {"x": 1}, lambda inputs, ctx: {"y": 0.5})
        [record] = self.records()
        self.assertEqual(record["output"], {"y": 0.5})

    def test_external_exchange_is_captured_in_full_within_the_trace(self) -> None:
        def execute(inputs, ctx):
            return ctx["io"].external("prices", {"symbol": "BTC"}, lambda r: {"price": 1.0})

        _runtime.run_brick("det", {}, execute)
        exchange, run = self.records()
        self.assertEqual(exchange["name"], "external:prices")
        self.assertEqual(exchange["response"], {"price": 1.0})
        self.assertEqual(exchange["trace_id"], run["trace_id"])
        self.assertEqual(exchange["run_id"], run["run_id"])

    def test_sibling_run_nests_in_the_same_trace(self) -> None:
        def child(inputs):
            return _runtime.run_brick("det", inputs, lambda i, c: {"ok": True})

        def parent(inputs, ctx):
            return ctx["io"].sibling("det", {"q": 1}, child)

        _runtime.run_brick("model", {}, parent)
        child_run, exchange, parent_run = self.records()
        self.assertEqual(child_run["parent_id"], parent_run["run_id"])
        self.assertEqual(len({child_run["trace_id"], exchange["trace_id"], parent_run["trace_id"]}), 1)
        self.assertNotIn("response", exchange)  # the sibling is deterministic: hash only

    def test_errors_are_captured_and_raised(self) -> None:
        def execute(inputs, ctx):
            raise ValueError("bad")

        with self.assertRaises(ValueError):
            _runtime.run_brick("det", {}, execute)
        [record] = self.records()
        self.assertEqual(record["error"], {"type": "ValueError", "message": "bad"})

    def test_installed_io_replaces_live(self) -> None:
        class Replay:
            def external(self, name, request, call):
                return {"replayed": name}

        token = _runtime.use_io(Replay())
        try:
            out = _runtime.run_brick("det", {}, lambda i, ctx: ctx["io"].external("src", {}, None))
        finally:
            _runtime._io.reset(token)
        self.assertEqual(out, {"replayed": "src"})

    def test_no_capture_without_the_environment_variable(self) -> None:
        with mock.patch.dict(os.environ, {_runtime.CAPTURE_ENV: ""}):
            _runtime.run_brick("det", {}, lambda i, c: {})
        self.assertEqual(self.records(), [])


if __name__ == "__main__":
    unittest.main()
