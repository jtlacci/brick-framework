"""Tests for deterministic host-to-Bend architecture extraction."""

from __future__ import annotations

from pathlib import Path
import os
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
        shutil.copytree(ROOT / "verification", self.root / "verification")
        shutil.copy(ROOT / "ARCHITECTURE.bend", self.root / "ARCHITECTURE.bend")
        (self.root / "tools").mkdir()
        shutil.copy(ROOT / "tools/model_repository.py", self.root / "tools/model_repository.py")

    def model(self) -> model_repository.RepositoryModel:
        return model_repository.build_model(self.root)

    def package(self, name: str) -> model_repository.PackageFact:
        return next(item for item in self.model().packages if item.name == name)

    def test_committed_model_matches_source(self) -> None:
        expected = model_repository.render(model_repository.build_model(ROOT))
        self.assertEqual((ROOT / "ARCHITECTURE.bend").read_text(encoding="utf-8"), expected)

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
        self.assertIn("False{}", model_repository.render(self.model()))

    def test_workflow_internal_import_is_extracted_for_bend_to_reject(self) -> None:
        path = self.root / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + "\nfrom bricks.example_brick.src import logic\n", encoding="utf-8")
        self.assertIn(
            model_repository.ImportFact("example_workflow", "example_brick", "flow", "internal"),
            self.model().imports,
        )

    def test_workflow_external_import_is_extracted_for_bend_to_reject(self) -> None:
        path = self.root / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + "\nimport requests\n", encoding="utf-8")
        self.assertIn(
            model_repository.ImportFact("example_workflow", None, "flow", "external"),
            self.model().imports,
        )

    def test_package_local_bend_code_becomes_false_shape_fact(self) -> None:
        (self.root / "bricks/example_brick/behavior.bend").write_text("def run():\n  Unit{}\n")
        self.assertFalse(self.package("example_brick").shape_valid)

    def test_dynamic_import_becomes_false_shape_fact(self) -> None:
        path = self.root / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + '\n__import__("requests")\n', encoding="utf-8")
        self.assertFalse(self.package("example_workflow").shape_valid)

    def test_unknown_dependency_uses_invalid_zero_id(self) -> None:
        path = self.root / "workflows/example_workflow/contract.py"
        path.write_text(path.read_text().replace('("example_brick",)', '("missing",)'), encoding="utf-8")
        self.assertIn("[0]", model_repository.render(self.model()))

    def test_check_detects_model_drift(self) -> None:
        path = self.root / "workflows/example_workflow/contract.py"
        path.write_text(path.read_text().replace("CONTRACT_VERSION = 1", "CONTRACT_VERSION = 2"), encoding="utf-8")
        result = subprocess.run(
            ["python3", "tools/model_repository.py", "--check"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        # Version changes are not architecture changes, so this remains current.
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
        self.assertIn("ARCHITECTURE.bend is stale", result.stderr)

    def test_render_is_independent_of_python_hash_seed(self) -> None:
        outputs = []
        for seed in ("1", "987654"):
            environment = dict(os.environ, PYTHONHASHSEED=seed)
            result = subprocess.run(
                ["python3", "tools/model_repository.py"],
                cwd=self.root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs.append(result.stdout)
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
