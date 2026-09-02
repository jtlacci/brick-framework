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


if __name__ == "__main__":
    unittest.main()
