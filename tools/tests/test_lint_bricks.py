"""Tests for tools/lint_bricks.py, standard library only.

Every test builds a throwaway repository from the committed boilerplate,
mutates one thing, and asserts on the exact message the linter reports.
The boilerplate itself must lint clean; that is the first test.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from tools import lint_bricks

ROOT = Path(__file__).resolve().parents[2]


class Fixture(unittest.TestCase):
    """A copy of the boilerplate under a temporary root, one brick per name."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="brick-lint-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        shutil.copy(ROOT / "AGENTS.md", self.root / "AGENTS.md")
        (self.root / "bricks").mkdir()
        shutil.copy(ROOT / "bricks/AGENTS.md", self.root / "bricks/AGENTS.md")
        shutil.copy(ROOT / "bricks/__init__.py", self.root / "bricks/__init__.py")

    def brick(self, name: str = "example_brick") -> Path:
        target = self.root / "bricks" / name
        shutil.copytree(ROOT / "bricks/example_brick", target, ignore=shutil.ignore_patterns("__pycache__"))
        return target

    def contract(self, brick: Path, **values: str) -> None:
        """Rewrite one or more top-level assignments in the brick's contract."""
        path = brick / "contract.py"
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        for name, value in values.items():
            for index, line in enumerate(lines):
                if line.startswith(f"{name}:") or line.startswith(f"{name} ="):
                    lines[index] = f"{name} = {value}\n"
                    break
            else:
                lines.append(f"{name} = {value}\n")
        path.write_text("".join(lines), encoding="utf-8")


    def pure_brick(self, name: str = "example_brick") -> Path:
        """The template with its one adapter and the evidence loader removed."""
        brick = self.brick(name)
        (brick / "input/adapters/example_source.py").unlink()
        (brick / "input/evidence.py").unlink()
        self.contract(brick, LANE='"pure"')
        return brick

    def errors(self) -> list[str]:
        return lint_bricks.lint_repo(self.root).errors

    def warnings(self) -> list[str]:
        return lint_bricks.lint_repo(self.root).warnings

    def assertError(self, fragment: str) -> None:
        errors = self.errors()
        self.assertTrue(any(fragment in item for item in errors), f"{fragment!r} not in {errors}")

    def assertClean(self) -> None:
        lint = lint_bricks.lint_repo(self.root)
        self.assertEqual(lint.errors, [])
        self.assertEqual(lint.warnings, [])


class BoilerplateTests(Fixture):
    def test_committed_boilerplate_lints_clean(self) -> None:
        self.assertClean()
        self.assertEqual(lint_bricks.lint_repo(ROOT).errors, [])

    def test_fixture_copy_lints_clean(self) -> None:
        self.brick()
        self.assertClean()

    def test_src_may_not_import_direct_io(self) -> None:
        brick = self.brick()
        (brick / "src/logic.py").write_text("import requests\n", encoding="utf-8")
        self.assertError("src imports direct-I/O module 'requests'")


class LaneTests(Fixture):
    def test_absent_lane_is_strict(self) -> None:
        brick = self.brick()
        self.assertNotIn("LANE", (brick / "contract.py").read_text(encoding="utf-8"))
        lint = lint_bricks.lint_repo(self.root)
        self.assertEqual(lint.errors, [])
        self.assertEqual(lint_bricks.lint_contract(brick, lint).lane, "strict")

    def test_every_lane_has_an_enforcer(self) -> None:
        self.assertIn("strict", lint_bricks.LANES)
        for lane, enforcer in lint_bricks.LANES.items():
            self.assertTrue(callable(enforcer), lane)

    def test_declared_strict_lints_clean(self) -> None:
        self.contract(self.brick(), LANE='"strict"')
        self.assertClean()

    def test_unknown_lane_is_an_error(self) -> None:
        self.contract(self.brick(), LANE='"permissive"')
        self.assertError("LANE must be one of")

    def test_non_string_lane_is_an_error(self) -> None:
        self.contract(self.brick(), LANE="1")
        self.assertError("LANE must be one of")


class PureLaneTests(Fixture):
    def test_pure_brick_lints_clean(self) -> None:
        self.pure_brick()
        self.assertClean()

    def test_template_is_not_pure(self) -> None:
        # The template ships one adapter and a filesystem evidence loader:
        # both are exactly what a pure brick gives up.
        self.contract(self.brick(), LANE='"pure"')
        self.assertError("pure brick may not have adapters")
        self.assertError("input/evidence.py: pure brick imports 'pathlib' outside runner/")

    def test_pure_brick_may_not_declare_sibling_dependencies(self) -> None:
        self.brick("other")
        self.contract(self.pure_brick(), SIBLING_DEPENDENCIES='{"other": "eventual"}')
        self.assertError("pure brick may not declare sibling dependencies")

    def test_pure_brick_bans_direct_io_outside_runner(self) -> None:
        brick = self.pure_brick()
        (brick / "input/loader.py").write_text("import os\n", encoding="utf-8")
        self.assertError("input/loader.py: pure brick imports 'os' outside runner/")

    def test_pure_brick_reports_src_direct_io_once(self) -> None:
        brick = self.pure_brick()
        (brick / "src/helpers.py").write_text("import os\n", encoding="utf-8")
        hits = [item for item in self.errors() if "src/helpers.py" in item]
        self.assertEqual(hits, ["bricks/example_brick/src/helpers.py: src imports direct-I/O module 'os'"])

    def test_pure_brick_bans_random_and_time_outside_runner(self) -> None:
        brick = self.pure_brick()
        (brick / "src/helpers.py").write_text("import random\nfrom time import sleep\n", encoding="utf-8")
        self.assertError("pure brick imports 'random' outside runner/")
        self.assertError("pure brick imports 'time' outside runner/")

    def test_pure_brick_runner_keeps_its_io(self) -> None:
        brick = self.pure_brick()
        (brick / "runner/rng.py").write_text("import random\nimport pathlib\nimport time\n", encoding="utf-8")
        self.assertClean()

    def test_pure_brick_may_not_read_the_clock(self) -> None:
        brick = self.pure_brick()
        (brick / "src/logic.py").write_text(
            "from datetime import datetime\n\n\ndef stamp():\n    return datetime.now()\n",
            encoding="utf-8",
        )
        self.assertError("src/logic.py: pure brick reads the clock with now()")

    def test_pure_brick_may_use_datetime_arithmetic(self) -> None:
        brick = self.pure_brick()
        (brick / "src/logic.py").write_text(
            "from datetime import datetime, timedelta\n\n\n"
            "def tomorrow(now: datetime) -> datetime:\n    return now + timedelta(days=1)\n",
            encoding="utf-8",
        )
        self.assertClean()

    def test_strict_brick_may_read_the_clock_in_src(self) -> None:
        brick = self.brick()
        (brick / "src/logic.py").write_text(
            "from datetime import datetime\n\n\ndef stamp():\n    return datetime.now()\n",
            encoding="utf-8",
        )
        self.assertClean()


SMOKE = (
    "import unittest\n\nfrom bricks.example_brick import run\n\n\n"
    "class SmokeTest(unittest.TestCase):\n"
    "    def test_run(self) -> None:\n"
    "        with self.assertRaises(NotImplementedError):\n"
    "            run({})\n"
)


class WorkflowLaneTests(Fixture):
    def workflow_brick(self, name: str = "example_brick") -> Path:
        brick = self.brick(name)
        self.contract(brick, LANE='"workflow"')
        return brick

    def smoke(self, brick: Path) -> None:
        tests = brick / "runner/tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_smoke.py").write_text(SMOKE, encoding="utf-8")

    def test_workflow_brick_lints_clean(self) -> None:
        self.workflow_brick()
        self.assertClean()

    def test_nothing_may_depend_on_a_workflow(self) -> None:
        self.workflow_brick("flow")
        self.contract(self.brick("lib"), SIBLING_DEPENDENCIES='{"flow": "eventual"}')
        self.assertError("bricks/lib/contract.py: sibling dependency 'flow' is a workflow brick")

    def test_workflow_may_have_a_process_door(self) -> None:
        brick = self.workflow_brick()
        (brick / "__main__.py").write_text("from . import run\n\nrun({})\n", encoding="utf-8")
        self.assertClean()

    def test_process_door_may_name_the_brick_in_full(self) -> None:
        brick = self.workflow_brick()
        (brick / "__main__.py").write_text("from bricks.example_brick import run\n\nrun({})\n", encoding="utf-8")
        self.assertClean()

    def test_process_door_may_import_only_run(self) -> None:
        brick = self.workflow_brick()
        (brick / "__main__.py").write_text("from .src.logic import execute\n", encoding="utf-8")
        self.assertError("__main__.py: __main__ may import only this brick's run")

    def test_process_door_may_not_reach_a_sibling(self) -> None:
        self.brick("other")
        brick = self.workflow_brick()
        (brick / "__main__.py").write_text("from bricks.other import run\n", encoding="utf-8")
        self.assertError("__main__.py: __main__ may import only this brick's run")

    def test_only_a_workflow_has_a_process_door(self) -> None:
        brick = self.brick()
        (brick / "__main__.py").write_text("from . import run\n", encoding="utf-8")
        self.assertError("__main__.py: only a workflow brick may have __main__.py")

    def test_smoke_tests_belong_to_workflows(self) -> None:
        self.smoke(self.workflow_brick())
        self.assertClean()

    def test_strict_brick_may_not_carry_smoke_tests(self) -> None:
        # Before lanes this was derived: a brick nothing depended on could carry
        # them. Now the brick says so, or it cannot.
        self.smoke(self.brick())
        self.assertError("runner/tests: smoke tests belong only to workflow bricks")


if __name__ == "__main__":
    unittest.main()
