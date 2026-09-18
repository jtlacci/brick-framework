"""Tests for the standard-library Bend brick linter."""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from tools import lint_bricks

ROOT = Path(__file__).resolve().parents[2]


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="bend-brick-lint-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        for name in ("AGENTS.md", "LAWS.bend", "PROOF.bend"):
            shutil.copy(ROOT / name, self.root / name)
        (self.root / "bricks").mkdir()
        shutil.copy(ROOT / "bricks/AGENTS.md", self.root / "bricks/AGENTS.md")

    def brick(self, name: str = "example_brick") -> Path:
        target = self.root / "bricks" / name
        shutil.copytree(ROOT / "bricks/example_brick", target)
        return target

    def definition(self, brick: Path, name: str, body: str) -> None:
        path = brick / "contract.bend"
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.startswith(f"def {name}("):
                body_index = index + 1
                while body_index < len(lines) and not lines[body_index].strip():
                    body_index += 1
                lines[body_index] = f"  {body}\n"
                path.write_text("".join(lines), encoding="utf-8")
                return
        self.fail(f"missing definition {name}")

    def lane(self, brick: Path, ctor: str) -> None:
        self.definition(brick, "lane", f"{ctor}{{}}")

    def dependencies(self, brick: Path, body: str) -> None:
        self.definition(brick, "sibling_dependencies", body)

    def owned(self, brick: Path, *resources: str) -> None:
        self.definition(brick, "owned_state", repr(list(resources)).replace("'", '"'))

    def pure_brick(self, name: str = "example_brick") -> Path:
        brick = self.brick(name)
        self.lane(brick, "Pure")
        (brick / "runner/run.bend").write_text(
            "import Base\nimport ../contract.bend as Contract\n"
            "import ../input/config.bend as Config\nimport ../src/logic.bend as Logic\n\n"
            "def run(input: Contract.BrickInput) -> IO(Contract.BrickOutput):\n"
            "  context = Config.run_context(0n)\n"
            "  IO.pure(Contract.BrickOutput, Logic.execute(input, context))\n",
            encoding="utf-8",
        )
        return brick

    def errors(self) -> list[str]:
        return lint_bricks.lint_repo(self.root).errors

    def warnings(self) -> list[str]:
        return lint_bricks.lint_repo(self.root).warnings

    def assertError(self, fragment: str) -> None:
        errors = self.errors()
        self.assertTrue(any(fragment in item for item in errors), f"{fragment!r} not in {errors}")

    def assertClean(self) -> None:
        result = lint_bricks.lint_repo(self.root)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])


class BoilerplateTests(Fixture):
    def test_committed_boilerplate_lints_clean(self) -> None:
        self.assertEqual(lint_bricks.lint_repo(ROOT).errors, [])

    def test_fixture_copy_lints_clean(self) -> None:
        self.brick()
        self.assertClean()

    def test_missing_required_path(self) -> None:
        brick = self.brick()
        (brick / "input/config.bend").unlink()
        self.assertError("input/config.bend: required brick path is missing")

    def test_python_runtime_is_rejected(self) -> None:
        brick = self.brick()
        (brick / "src/logic.py").write_text("pass\n", encoding="utf-8")
        self.assertError("Python runtime code is not allowed inside a Bend brick")

    def test_entry_must_define_only_run(self) -> None:
        brick = self.brick()
        with (brick / "main.bend").open("a", encoding="utf-8") as handle:
            handle.write("\ndef leak() -> U32:\n  0\n")
        self.assertError("must define only the public run entry point")

    def test_entry_signature_is_checked(self) -> None:
        brick = self.brick()
        path = brick / "main.bend"
        path.write_text(path.read_text().replace("IO(Contract.BrickOutput)", "Contract.BrickOutput"))
        self.assertError("return IO(Contract.BrickOutput)")


class ContractTests(Fixture):
    def test_every_lane_has_an_enforcer(self) -> None:
        self.assertEqual(set(lint_bricks.LANES), {"strict", "pure", "workflow"})
        self.assertTrue(all(callable(item) for item in lint_bricks.LANES.values()))

    def test_version_must_be_positive_literal(self) -> None:
        self.definition(self.brick(), "contract_version", "0")
        self.assertError("positive U32 literal")

    def test_lane_must_be_literal_constructor(self) -> None:
        self.definition(self.brick(), "lane", "choose_lane()")
        self.assertError("lane must return Strict{}, Pure{}, or Workflow{} literally")

    def test_dependencies_must_be_literal(self) -> None:
        self.dependencies(self.brick(), "load_dependencies()")
        self.assertError("sibling_dependencies must be a literal list")

    def test_owned_state_must_be_strings(self) -> None:
        self.definition(self.brick(), "owned_state", "[1]")
        self.assertError("owned_state must be a literal list of non-empty strings")


class BoundaryTests(Fixture):
    def sibling_adapter(self, brick: Path, sibling: str) -> None:
        (brick / f"input/adapters/{sibling}.bend").write_text(
            f"import Base\nimport ../../../{sibling}/contract.bend as SiblingContract\n"
            f"import ../../../{sibling}/main.bend as Sibling\n",
            encoding="utf-8",
        )

    def test_declared_sibling_adapter_lints_clean(self) -> None:
        owner = self.brick("owner")
        self.brick("other")
        self.dependencies(owner, '[Dependency{"other", Eventual{}}]')
        self.sibling_adapter(owner, "other")
        self.assertClean()

    def test_undeclared_sibling_is_rejected(self) -> None:
        owner = self.brick("owner")
        self.brick("other")
        self.sibling_adapter(owner, "other")
        self.assertError("sibling dependency 'other' is not declared")

    def test_declared_but_unused_dependency_warns(self) -> None:
        owner = self.brick("owner")
        self.brick("other")
        self.dependencies(owner, '[Dependency{"other", Eventual{}}]')
        self.assertIn("declared dependency 'other' has no static adapter import", "\n".join(self.warnings()))

    def test_src_may_not_import_sibling(self) -> None:
        owner = self.brick("owner")
        self.brick("other")
        self.dependencies(owner, '[Dependency{"other", Eventual{}}]')
        (owner / "src/coupled.bend").write_text(
            "import ../../other/main.bend as Other\n", encoding="utf-8"
        )
        self.assertError("only an input adapter may import a sibling brick")

    def test_src_may_not_perform_effects(self) -> None:
        brick = self.brick()
        (brick / "src/effect.bend").write_text(
            'import Base\ndef bad() -> IO(Unit):\n  IO.print("bad")\n', encoding="utf-8"
        )
        self.assertError("src performs a direct effect")

    def test_unsafe_and_open_todo_are_rejected(self) -> None:
        brick = self.brick()
        (brick / "src/bad.bend").write_text(
            "import Base\n@unsafe def bad() -> U32:\n  ?TODO\n", encoding="utf-8"
        )
        self.assertError("@unsafe is forbidden")
        self.assertError("contains an unresolved TODO")

    def test_adapter_foreign_effect_needs_both_backends(self) -> None:
        brick = self.brick()
        adapter = brick / "input/adapters/source.bend"
        adapter.write_text(
            'import Base\ndef fetch() -> IO(Unit):\n  import "./fetch.c"\n',
            encoding="utf-8",
        )
        (adapter.parent / "fetch.c").write_text("/* host effect */\n", encoding="utf-8")
        self.assertError("needs paired .c and .js implementations")

    def test_adapter_paired_foreign_effect_lints_clean(self) -> None:
        brick = self.brick()
        adapter = brick / "input/adapters/source.bend"
        adapter.write_text(
            'import Base\ndef fetch() -> IO(Unit):\n  import "./fetch.c"\n  import "./fetch.js"\n',
            encoding="utf-8",
        )
        (adapter.parent / "fetch.c").write_text("/* host effect */\n", encoding="utf-8")
        (adapter.parent / "fetch.js").write_text("// host effect\n", encoding="utf-8")
        self.assertClean()


class GraphTests(Fixture):
    def test_duplicate_state_owner_is_rejected(self) -> None:
        self.owned(self.brick("one"), "db:records")
        self.owned(self.brick("two"), "db:records")
        self.assertError("is already owned by 'one'")

    def test_dependency_cycle_is_rejected(self) -> None:
        one = self.brick("one")
        two = self.brick("two")
        self.dependencies(one, '[Dependency{"two", Eventual{}}]')
        self.dependencies(two, '[Dependency{"one", Orchestrated{}}]')
        self.sibling(one, "two")
        self.sibling(two, "one")
        self.assertError("sibling dependency cycle")

    @staticmethod
    def sibling(brick: Path, sibling: str) -> None:
        (brick / f"input/adapters/{sibling}.bend").write_text(
            f"import Base\nimport ../../../{sibling}/contract.bend as SiblingContract\n"
            f"import ../../../{sibling}/main.bend as Sibling\n", encoding="utf-8"
        )

    def test_nothing_may_depend_on_workflow(self) -> None:
        flow = self.brick("flow")
        owner = self.brick("owner")
        self.lane(flow, "Workflow")
        self.dependencies(owner, '[Dependency{"flow", Orchestrated{}}]')
        self.sibling(owner, "flow")
        self.assertError("sibling dependency 'flow' is a workflow brick")


class PureLaneTests(Fixture):
    def test_pure_brick_lints_clean(self) -> None:
        self.pure_brick()
        self.assertClean()

    def test_pure_brick_may_not_have_adapter(self) -> None:
        brick = self.pure_brick()
        (brick / "input/adapters/source.bend").write_text("import Base\n", encoding="utf-8")
        self.assertError("pure brick may not have adapters")

    def test_pure_brick_may_not_read_clock_in_runner(self) -> None:
        brick = self.pure_brick()
        path = brick / "runner/run.bend"
        path.write_text(path.read_text().replace("IO.pure", "IO.now # IO.pure"), encoding="utf-8")
        self.assertError("pure brick may not perform effects")

    def test_pure_brick_may_not_depend_on_sibling(self) -> None:
        brick = self.pure_brick()
        self.brick("other")
        self.dependencies(brick, '[Dependency{"other", Eventual{}}]')
        self.assertError("pure brick may not declare sibling dependencies")


class WorkflowLaneTests(Fixture):
    def workflow(self) -> Path:
        brick = self.brick()
        self.lane(brick, "Workflow")
        return brick

    def test_workflow_app_lints_clean(self) -> None:
        brick = self.workflow()
        (brick / "app.bend").write_text(
            "import Base\nimport ./main.bend as Brick\n\ndef main() -> IO(Unit):\n  IO.print(\"ok\")\n",
            encoding="utf-8",
        )
        self.assertClean()

    def test_only_workflow_may_have_app(self) -> None:
        brick = self.brick()
        (brick / "app.bend").write_text("import Base\ndef main() -> IO(Unit):\n  IO.print(\"x\")\n")
        self.assertError("only a workflow brick may have app.bend")

    def test_smoke_programs_belong_to_workflow(self) -> None:
        brick = self.brick()
        tests = brick / "runner/tests"
        tests.mkdir()
        (tests / "smoke.bend").write_text(
            "import Base\nimport ../../main.bend as Brick\ndef main() -> IO(Unit):\n  IO.print(\"ok\")\n"
        )
        self.assertError("smoke programs belong only to workflow bricks")


if __name__ == "__main__":
    unittest.main()
