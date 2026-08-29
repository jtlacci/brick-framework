"""One smoke-test input passed directly to run()."""

from modules.example_module.runner.run import run


TEST_INPUT = {}


def test_smoke() -> None:
    run(TEST_INPUT)
