"""End-to-end tests for the framework linter and reusable workflows."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ToolchainWorkflowTests(unittest.TestCase):
    def workflow(self, name: str) -> str:
        return (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")

    def test_validation_runs_the_framework_linter(self) -> None:
        text = self.workflow("validate.yml")
        self.assertIn(".brick-framework/tools/model_repository.py --root . --check", text)

    def test_validation_has_an_opt_in_strict_connection_gate(self) -> None:
        text = self.workflow("validate.yml")
        self.assertIn("type_check:", text)
        self.assertIn("type_check_requirements:", text)
        self.assertIn("default: false", text)
        self.assertIn("requirements-typecheck.txt", text)
        self.assertIn("python3 -m mypy", text)
        self.assertIn("tools/check_typing_fixture.py", text)
        self.assertLess(text.index("python3 -m mypy"), text.index("model_repository.py"))

    def test_connection_type_checker_is_pinned_and_fail_closed(self) -> None:
        requirements = (ROOT / "requirements-typecheck.txt").read_text(encoding="utf-8")
        config = (ROOT / "mypy.ini").read_text(encoding="utf-8")
        self.assertEqual(requirements.strip(), "mypy==2.3.1")
        self.assertIn("strict = True", config)
        self.assertIn("python_version = 3.12", config)
        self.assertNotIn("ignore_missing_imports", config)

    def test_reusable_workflows_require_an_immutable_framework_ref(self) -> None:
        text = self.workflow("validate.yml")
        declaration = re.search(r"framework-ref:\n(?P<body>(?:        .+\n)+)", text)
        self.assertIsNotNone(declaration)
        self.assertIn("required: true", declaration.group("body"))
        self.assertIn("framework-ref must be a full 40-character commit SHA", text)


class RepositoryLinterTests(unittest.TestCase):
    def copy_repo(self) -> Path:
        directory = tempfile.mkdtemp(prefix="brick-linter-")
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        copy = Path(directory) / "repo"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__", "*.pyc"))
        return copy

    def lint(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "tools/model_repository.py", "--root", ".", "--check"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )

    def assert_invalid(self, root: Path, fragment: str) -> None:
        result = self.lint(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(fragment, result.stderr)

    def test_current_repository_is_valid(self) -> None:
        result = self.lint(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_required_file_is_rejected(self) -> None:
        copy = self.copy_repo()
        (copy / "bricks/example_brick/src/logic.py").unlink()
        self.assert_invalid(copy, "missing required path src/logic.py")

    def test_workflow_internal_import_is_rejected(self) -> None:
        copy = self.copy_repo()
        path = copy / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + "\nfrom bricks.example_brick.src import logic\n", encoding="utf-8")
        self.assert_invalid(copy, "flow may not import internal surface")

    def test_workflow_external_effect_is_rejected(self) -> None:
        copy = self.copy_repo()
        path = copy / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + "\nimport requests\n", encoding="utf-8")
        self.assert_invalid(copy, "external capability is allowed only")

    def test_contract_import_does_not_satisfy_executable_dependency(self) -> None:
        copy = self.copy_repo()
        path = copy / "workflows/example_workflow/flow.py"
        path.write_text(
            path.read_text()
            .replace(
                "from bricks.example_brick import run as run_example_brick\n",
                "from bricks.example_brick.contract import BrickInput\n",
            )
            .replace("return run_example_brick(inputs)", "return BrickInput(**inputs)"),
            encoding="utf-8",
        )
        self.assert_invalid(copy, "has no public run import")

    def test_strict_brick_adapter_may_own_an_external_effect(self) -> None:
        copy = self.copy_repo()
        (copy / "bricks/example_brick/input/adapters/source.py").write_text(
            "def read_records():\n    return open('records.json')\n", encoding="utf-8"
        )
        result = self.lint(copy)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
