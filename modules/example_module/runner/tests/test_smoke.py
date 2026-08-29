"""One smoke-test input passed directly to run()."""

import unittest

from modules.example_module.runner.run import run


TEST_INPUT = {}


class SmokeTest(unittest.TestCase):
    @unittest.skip("TODO: implement run()")
    def test_smoke(self) -> None:
        run(TEST_INPUT)
