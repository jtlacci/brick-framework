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
        shutil.copy(ROOT / "AGENTS.md", self.root / "AGENTS.md")
        (self.root / "LAWS.bend").write_text("import Base\n", encoding="utf-8")
        (self.root / "PROOF.bend").write_text(
            "import Base\nimport ./LAWS.bend as Laws\n", encoding="utf-8"
        )
        (self.root / "bricks").mkdir()
        shutil.copy(ROOT / "bricks/AGENTS.md", self.root / "bricks/AGENTS.md")
        (self.root / "workflows").mkdir()
        shutil.copy(ROOT / "workflows/AGENTS.md", self.root / "workflows/AGENTS.md")

    def brick(self, name: str = "example_brick") -> Path:
        target = self.root / "bricks" / name
        shutil.copytree(ROOT / "bricks/example_brick", target)
        self.sync_aggregators()
        return target

    def sync_aggregators(self) -> None:
        names = sorted(path.name for path in (self.root / "bricks").iterdir() if path.is_dir())
        workflow_names = sorted(
            path.name for path in (self.root / "workflows").iterdir() if path.is_dir()
        )
        laws = ["# Test root law aggregation.", "import Base"]
        proofs = ["# Test root proof aggregation.", "import Base", "import ./LAWS.bend as Laws"]
        for index, name in enumerate(names):
            laws.append(f"import ./bricks/{name}/laws.bend as Brick{index}Laws")
            proofs.append(f"import ./bricks/{name}/proof.bend as Brick{index}Proof")
        for index, name in enumerate(workflow_names):
            laws.append(f"import ./workflows/{name}/laws.bend as Workflow{index}Laws")
            proofs.append(f"import ./workflows/{name}/proof.bend as Workflow{index}Proof")
        (self.root / "LAWS.bend").write_text("\n".join(laws) + "\n", encoding="utf-8")
        (self.root / "PROOF.bend").write_text("\n".join(proofs) + "\n", encoding="utf-8")

    def workflow(self, name: str = "double_value") -> Path:
        if not (self.root / "bricks/example_brick").exists():
            self.brick()
        target = self.root / "workflows" / name
        shutil.copytree(ROOT / "workflows/double_value", target)
        self.sync_aggregators()
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

    def test_brick_laws_and_proof_are_required(self) -> None:
        brick = self.brick()
        (brick / "laws.bend").unlink()
        (brick / "proof.bend").unlink()
        self.assertError("laws.bend: required brick path is missing")
        self.assertError("proof.bend: required brick path is missing")

    def test_root_must_aggregate_every_brick_law_and_proof(self) -> None:
        self.brick()
        (self.root / "LAWS.bend").write_text("import Base\n", encoding="utf-8")
        (self.root / "PROOF.bend").write_text(
            "import Base\nimport ./LAWS.bend as Laws\n", encoding="utf-8"
        )
        self.assertError("must aggregate bricks/example_brick/laws.bend")
        self.assertError("must aggregate bricks/example_brick/proof.bend")

    def test_brick_proof_must_import_its_laws(self) -> None:
        brick = self.brick()
        (brick / "proof.bend").write_text("import Base\n", encoding="utf-8")
        self.assertError("must import its own ./laws.bend")

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
        self.assertEqual(set(lint_bricks.LANES), {"strict", "pure"})
        self.assertTrue(all(callable(item) for item in lint_bricks.LANES.values()))

    def test_version_must_be_positive_literal(self) -> None:
        self.definition(self.brick(), "contract_version", "0")
        self.assertError("positive U32 literal")

    def test_lane_must_be_literal_constructor(self) -> None:
        self.definition(self.brick(), "lane", "choose_lane()")
        self.assertError("lane must return Strict{} or Pure{} literally")

    def test_workflow_is_not_a_brick_lane(self) -> None:
        self.lane(self.brick(), "Workflow")
        self.assertError("lane must return Strict{} or Pure{} literally")

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
            f"import ../../../{sibling}/main.bend as Sibling\n\n"
            "def call(input: SiblingContract.BrickInput) -> IO(SiblingContract.BrickOutput):\n"
            "  Sibling.run(input)\n",
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
            f"import ../../../{sibling}/main.bend as Sibling\n\n"
            "def call(input: SiblingContract.BrickInput) -> IO(SiblingContract.BrickOutput):\n"
            "  Sibling.run(input)\n", encoding="utf-8"
        )

    def test_brick_may_not_import_workflow(self) -> None:
        owner = self.brick("owner")
        self.workflow()
        (owner / "src/coupled.bend").write_text(
            "import ../../../workflows/double_value/main.bend as Workflow\n",
            encoding="utf-8",
        )
        self.assertError("brick may not import a workflow")


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


class WorkflowTests(Fixture):
    def test_workflow_lints_clean(self) -> None:
        self.workflow()
        self.assertClean()

    def test_brick_may_not_have_app(self) -> None:
        brick = self.brick()
        (brick / "app.bend").write_text("import Base\ndef main() -> IO(Unit):\n  IO.print(\"x\")\n")
        self.assertError("app.bend belongs in a workflow")

    def test_brick_may_not_have_whole_use_case_smokes(self) -> None:
        brick = self.brick()
        tests = brick / "runner/tests"
        tests.mkdir()
        (tests / "smoke.bend").write_text(
            "import Base\nimport ../../main.bend as Brick\ndef main() -> IO(Unit):\n  IO.print(\"ok\")\n"
        )
        self.assertError("whole-use-case smoke programs belong in workflows")

    def test_workflow_dependency_must_be_literal(self) -> None:
        workflow = self.workflow()
        path = workflow / "contract.bend"
        path.write_text(
            path.read_text().replace(
                '[BrickDependency{"example_brick"}]', "load_dependencies()"
            ),
            encoding="utf-8",
        )
        self.assertError("brick_dependencies must be a literal list")

    def test_root_must_aggregate_workflow_law_and_proof(self) -> None:
        self.workflow()
        (self.root / "LAWS.bend").write_text("import Base\n", encoding="utf-8")
        (self.root / "PROOF.bend").write_text(
            "import Base\nimport ./LAWS.bend as Laws\n", encoding="utf-8"
        )
        self.assertError("must aggregate workflows/double_value/laws.bend")
        self.assertError("must aggregate workflows/double_value/proof.bend")

    def test_workflow_declared_and_imported_bricks_must_match(self) -> None:
        workflow = self.workflow()
        path = workflow / "contract.bend"
        path.write_text(
            path.read_text().replace("example_brick", "missing_brick"),
            encoding="utf-8",
        )
        self.assertError("unknown brick dependency 'missing_brick'")
        self.assertError("brick dependency 'example_brick' is not declared")

    def test_workflow_may_not_perform_direct_effect(self) -> None:
        workflow = self.workflow()
        path = workflow / "flow.bend"
        path.write_text(path.read_text() + '\ndef bad() -> IO(Unit):\n  IO.print("bad")\n')
        self.assertError("workflow may not perform a direct effect; use a brick")

    def test_workflow_may_not_import_another_workflow(self) -> None:
        workflow = self.workflow()
        other = self.root / "workflows/other"
        shutil.copytree(ROOT / "workflows/double_value", other)
        self.sync_aggregators()
        path = workflow / "flow.bend"
        path.write_text(
            path.read_text() + "\nimport ../other/main.bend as Other\n",
            encoding="utf-8",
        )
        self.assertError("workflow may not import another workflow")

    def test_workflow_may_not_import_brick_internals(self) -> None:
        workflow = self.workflow()
        path = workflow / "flow.bend"
        path.write_text(
            path.read_text()
            + "\nimport ../../bricks/example_brick/runner/run.bend as Internal\n",
            encoding="utf-8",
        )
        self.assertError("workflow may import only brick main.bend and contract.bend")

    def test_workflow_smoke_uses_only_public_boundary(self) -> None:
        workflow = self.workflow()
        path = workflow / "tests/smoke.bend"
        path.write_text(path.read_text() + "\nimport ../flow.bend as Flow\n", encoding="utf-8")
        self.assertError("smoke program may import only Base")

    def test_workflow_requires_a_smoke(self) -> None:
        workflow = self.workflow()
        (workflow / "tests/smoke.bend").unlink()
        self.assertError("workflow must have one to three Bend smoke programs")


if __name__ == "__main__":
    unittest.main()
