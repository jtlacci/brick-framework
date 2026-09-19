"""Tests for deterministic repository architecture enforcement."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools import model_repository


ROOT = Path(__file__).resolve().parents[2]


class ModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="brick-model-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        shutil.copytree(ROOT / "bricks", self.root / "bricks")
        shutil.copytree(ROOT / "workflows", self.root / "workflows")
        (self.root / "tools").mkdir()
        shutil.copy(ROOT / "tools/model_repository.py", self.root / "tools/model_repository.py")

    def model(self) -> model_repository.RepositoryModel:
        return model_repository.build_model(self.root)

    def package(self, name: str) -> model_repository.PackageFact:
        return next(item for item in self.model().packages if item.name == name)

    def errors(self) -> list[str]:
        return model_repository.validation_errors(self.model())

    def assert_invalid(self, fragment: str) -> None:
        errors = self.errors()
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_example_repository_is_structurally_valid(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_example_facts_are_language_neutral_architecture(self) -> None:
        model = self.model()
        self.assertEqual([item.name for item in model.packages], ["example_brick", "example_workflow"])
        self.assertEqual(self.package("example_workflow").dependencies, ("example_brick",))
        self.assertEqual(model.ranks, {"example_brick": 0, "example_workflow": 1})
        self.assertEqual(
            model.imports,
            [model_repository.ImportFact("example_workflow", "example_brick", "flow", "entry")],
        )

    def test_missing_required_file_becomes_false_shape_fact(self) -> None:
        (self.root / "bricks/example_brick/src/logic.py").unlink()
        package = self.package("example_brick")
        self.assertFalse(package.shape_valid)
        self.assertIn("missing required path src/logic.py", package.issues)
        self.assert_invalid("missing required path src/logic.py")

    def test_workflow_internal_import_is_rejected(self) -> None:
        path = self.root / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + "\nfrom bricks.example_brick.src import logic\n", encoding="utf-8")
        self.assertIn(
            model_repository.ImportFact("example_workflow", "example_brick", "flow", "internal"),
            self.model().imports,
        )
        self.assert_invalid("flow may not import internal surface")

    def test_workflow_external_import_is_rejected(self) -> None:
        path = self.root / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + "\nimport requests\n", encoding="utf-8")
        self.assertIn(
            model_repository.ImportFact("example_workflow", None, "flow", "external"),
            self.model().imports,
        )
        self.assert_invalid("external capability is allowed only")

    def test_dynamic_import_becomes_false_shape_fact(self) -> None:
        path = self.root / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + '\n__import__("requests")\n', encoding="utf-8")
        self.assertFalse(self.package("example_workflow").shape_valid)

    def test_run_requires_exactly_one_required_input(self) -> None:
        path = self.root / "workflows/example_workflow/flow.py"
        original = path.read_text(encoding="utf-8")
        signatures = (
            "inputs: WorkflowInput, extra: object",
            "inputs: WorkflowInput, *extra: object",
            "inputs: WorkflowInput, *, extra: object",
            'inputs: WorkflowInput = {"value": 0}',
        )
        for signature in signatures:
            with self.subTest(signature=signature):
                path.write_text(
                    original.replace("inputs: WorkflowInput", signature), encoding="utf-8"
                )
                package = self.package("example_workflow")
                self.assertFalse(package.shape_valid)
                self.assertIn(
                    "run must accept exactly one required positional input", package.issues
                )
        path.write_text(original, encoding="utf-8")

    def test_run_must_be_synchronous_undecorated_and_unique(self) -> None:
        path = self.root / "workflows/example_workflow/flow.py"
        original = path.read_text(encoding="utf-8")
        cases = (
            (original.replace("def run(", "async def run("), "exactly one synchronous"),
            (original.replace("def run(", "@staticmethod\ndef run("), "run may not be decorated"),
            (original + "\n" + original[original.index("def run(") :], "exactly one synchronous"),
        )
        for source, issue in cases:
            with self.subTest(issue=issue):
                path.write_text(source, encoding="utf-8")
                package = self.package("example_workflow")
                self.assertFalse(package.shape_valid)
                self.assertTrue(any(issue in item for item in package.issues), package.issues)
        path.write_text(original, encoding="utf-8")

    def test_obvious_external_calls_are_extracted_with_aliases(self) -> None:
        path = self.root / "bricks/example_brick/src/logic.py"
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\nimport random as rng\n"
            + "from datetime import datetime as Clock\n"
            + "from time import time as now\n\n"
            + "def hidden_inputs():\n"
            + "    open('records.json')\n"
            + "    return rng.random(), Clock.now(), Clock.utcnow(), now()\n",
            encoding="utf-8",
        )
        external = [
            item
            for item in self.model().imports
            if item.source == "example_brick" and item.surface == "external"
        ]
        self.assertEqual(len(external), 5)
        self.assertTrue(all(item.role == "other" for item in external))
        self.assert_invalid("external capability is allowed only")

    def test_seeded_random_and_datetime_arithmetic_are_not_effects(self) -> None:
        path = self.root / "bricks/example_brick/src/logic.py"
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\nfrom datetime import timedelta\n"
            + "from random import Random\n\n"
            + "def deterministic(seed: int):\n"
            + "    return Random(seed).random(), timedelta(seconds=seed)\n",
            encoding="utf-8",
        )
        self.assertFalse(
            any(
                item.source == "example_brick" and item.surface == "external"
                for item in self.model().imports
            )
        )

    def test_unknown_dependency_is_invalid(self) -> None:
        path = self.root / "workflows/example_workflow/contract.py"
        path.write_text(path.read_text().replace('("example_brick",)', '("missing",)'), encoding="utf-8")
        self.assert_invalid("unknown dependency 'missing'")

    def test_declared_dependency_requires_public_run_import(self) -> None:
        path = self.root / "workflows/example_workflow/flow.py"
        path.write_text(
            path.read_text(encoding="utf-8")
            .replace(
                "from bricks.example_brick import run as run_example_brick\n",
                "from bricks.example_brick.contract import BrickInput\n",
            )
            .replace("return run_example_brick(inputs)", "return BrickInput(**inputs)"),
            encoding="utf-8",
        )
        self.assert_invalid("has no public run import")

    def test_undeclared_dependency_import_is_invalid(self) -> None:
        contract = self.root / "workflows/example_workflow/contract.py"
        contract.write_text(
            contract.read_text(encoding="utf-8").replace(
                '("example_brick",)', "()"
            ),
            encoding="utf-8",
        )
        self.assert_invalid("import of 'example_brick' is not declared")

    def test_unknown_library_is_an_external_capability(self) -> None:
        path = self.root / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + "\nimport acme_cloud_sdk\n", encoding="utf-8")
        self.assert_invalid("external capability is allowed only")

    def test_relative_sibling_import_is_resolved(self) -> None:
        source = self.root / "bricks/example_brick"
        other = self.root / "bricks/other"
        shutil.copytree(source, other)
        contract = source / "contract.py"
        contract.write_text(
            contract.read_text().replace(
                "SIBLING_DEPENDENCIES: dict[str, str] = {}",
                'SIBLING_DEPENDENCIES = {"other": "orchestrated"}',
            ),
            encoding="utf-8",
        )
        (source / "input/adapters/other.py").write_text(
            "from ....other import run\n", encoding="utf-8"
        )
        self.assertIn(
            model_repository.ImportFact("example_brick", "other", "adapter", "entry"),
            self.model().imports,
        )
        self.assertEqual(self.errors(), [])

    def test_pure_brick_rejects_dependencies_and_external_effects(self) -> None:
        source = self.root / "bricks/example_brick"
        other = self.root / "bricks/other"
        shutil.copytree(source, other)
        contract = source / "contract.py"
        contract.write_text(
            contract.read_text()
            .replace('LANE = "strict"', 'LANE = "pure"')
            .replace(
                "SIBLING_DEPENDENCIES: dict[str, str] = {}",
                'SIBLING_DEPENDENCIES = {"other": "orchestrated"}',
            ),
            encoding="utf-8",
        )
        (source / "input/adapters/other.py").write_text(
            "from bricks.other import run\nimport requests\n", encoding="utf-8"
        )
        self.assert_invalid("pure brick example_brick: may not declare dependencies")
        self.assert_invalid("external capability is allowed only")

    def test_workflow_state_is_invalid(self) -> None:
        contract = self.root / "workflows/example_workflow/contract.py"
        contract.write_text(
            contract.read_text() + '\nOWNED_STATE = ("db:workflow",)\n', encoding="utf-8"
        )
        self.assert_invalid("workflow example_workflow: may not own state")

    def test_dependency_cycle_is_invalid(self) -> None:
        source = self.root / "bricks/example_brick"
        other = self.root / "bricks/other"
        shutil.copytree(source, other)
        for path, dependency in (
            (source, "other"),
            (other, "example_brick"),
        ):
            contract = path / "contract.py"
            contract.write_text(
                contract.read_text().replace(
                    "SIBLING_DEPENDENCIES: dict[str, str] = {}",
                    f'SIBLING_DEPENDENCIES = {{"{dependency}": "orchestrated"}}',
                ),
                encoding="utf-8",
            )
            (path / f"input/adapters/{dependency}.py").write_text(
                f"from bricks.{dependency} import run\n", encoding="utf-8"
            )
        self.assert_invalid("creates a cycle")

    def test_duplicate_state_owner_is_invalid(self) -> None:
        source = self.root / "bricks/example_brick"
        other = self.root / "bricks/other"
        shutil.copytree(source, other)
        for contract in (source / "contract.py", other / "contract.py"):
            contract.write_text(
                contract.read_text().replace(
                    "OWNED_STATE: tuple[str, ...] = ()", 'OWNED_STATE = ("db:records",)'
                ),
                encoding="utf-8",
            )
        self.assert_invalid("is owned by both")

    def test_cli_validates_current_source_directly(self) -> None:
        path = self.root / "workflows/example_workflow/contract.py"
        path.write_text(path.read_text().replace("CONTRACT_VERSION = 1", "CONTRACT_VERSION = 2"), encoding="utf-8")
        result = subprocess.run(
            ["python3", "tools/model_repository.py", "--check"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        # Version changes are valid metadata changes.
        self.assertEqual(result.returncode, 0, result.stderr)
        path.write_text(path.read_text().replace('("example_brick",)', "()"), encoding="utf-8")
        result = subprocess.run(
            ["python3", "tools/model_repository.py", "--check"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("import of 'example_brick' is not declared", result.stderr)


if __name__ == "__main__":
    unittest.main()
