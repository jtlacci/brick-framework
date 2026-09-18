"""Compiler-backed tests for the generated architecture and stable Bend law."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PINNED_BEND = (ROOT / ".bend-version").read_text(encoding="utf-8").strip()


class ToolchainWorkflowTests(unittest.TestCase):
    def workflow(self, name: str) -> str:
        return (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")

    def test_workflows_pin_the_repository_bend_version_and_checksum(self) -> None:
        checksums: set[str] = set()
        for name in ("validate.yml", "review.yml"):
            text = self.workflow(name)
            self.assertIn(f'BEND_VERSION: "{PINNED_BEND}"', text)
            matches = re.findall(r'BEND_SHA256: "([0-9a-f]{64})"', text)
            self.assertEqual(len(matches), 1)
            checksums.update(matches)
        self.assertEqual(len(checksums), 1)

    def test_ci_checks_model_drift_then_framework_proof(self) -> None:
        for name in ("validate.yml", "review.yml"):
            text = self.workflow(name)
            self.assertIn("model_repository.py", text)
            self.assertIn("--check", text)
            self.assertIn("bend PROOF.bend", text)
            self.assertNotIn("find bricks", text)
            self.assertNotIn("find workflows", text)

    def test_review_validation_precedes_optional_model_review(self) -> None:
        text = self.workflow("review.yml")
        validation = text.index("- name: validate generated Bend architecture")
        self.assertLess(validation, text.index("- id: key"))

    def test_reusable_workflows_require_an_immutable_framework_ref(self) -> None:
        for name in ("validate.yml", "review.yml"):
            text = self.workflow(name)
            declaration = re.search(r"framework-ref:\n(?P<body>(?:        .+\n)+)", text)
            self.assertIsNotNone(declaration)
            self.assertIn("required: true", declaration.group("body"))
            self.assertIn("framework-ref must be a full 40-character commit SHA", text)


class BendVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        requested = os.environ.get("BEND_BIN", "bend")
        cls.bend = shutil.which(requested)
        if cls.bend is None:
            message = f"Bend executable not found: {requested}"
            if os.environ.get("BEND_REQUIRED") == "1":
                raise RuntimeError(message)
            raise unittest.SkipTest(message)

    def bend_run(self, *arguments: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.bend, *arguments], cwd=cwd, check=False, capture_output=True, text=True
        )

    def copy_repo(self) -> Path:
        directory = tempfile.mkdtemp(prefix="bend-verifier-")
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        copy = Path(directory) / "repo"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        return copy

    def regenerate(self, root: Path) -> None:
        result = subprocess.run(
            ["python3", "tools/model_repository.py", "--write"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_invalid(self, root: Path) -> None:
        self.regenerate(root)
        result = self.bend_run("PROOF.bend", cwd=root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pinned_compiler_version(self) -> None:
        result = self.bend_run("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"bend {PINNED_BEND}")

    def test_stable_framework_proof_accepts_committed_model(self) -> None:
        result = self.bend_run("PROOF.bend")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "All terms check.")

    def test_directly_corrupted_architecture_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        architecture = copy / "ARCHITECTURE.bend"
        valid = architecture.read_text(encoding="utf-8")
        invalid = valid.replace("Rules.Entry{}", "Rules.Internal{}")
        self.assertNotEqual(invalid, valid)
        architecture.write_text(invalid, encoding="utf-8")
        result = self.bend_run("PROOF.bend", cwd=copy)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_no_package_behavior_is_implemented_in_bend(self) -> None:
        self.assertEqual(list((ROOT / "bricks").rglob("*.bend")), [])
        self.assertEqual(list((ROOT / "workflows").rglob("*.bend")), [])

    def test_missing_host_file_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        (copy / "bricks/example_brick/src/logic.py").unlink()
        self.assert_invalid(copy)

    def test_workflow_internal_import_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        path = copy / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + "\nfrom bricks.example_brick.src import logic\n", encoding="utf-8")
        self.assert_invalid(copy)

    def test_workflow_external_import_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        path = copy / "workflows/example_workflow/flow.py"
        path.write_text(path.read_text() + "\nimport requests\n", encoding="utf-8")
        self.assert_invalid(copy)

    def test_declared_but_unused_dependency_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        path = copy / "workflows/example_workflow/flow.py"
        path.write_text(
            path.read_text().replace(
                "from bricks.example_brick import run as run_example_brick\n", ""
            ).replace("    return run_example_brick(inputs)", "    raise NotImplementedError"),
            encoding="utf-8",
        )
        self.assert_invalid(copy)

    def test_contract_import_does_not_satisfy_executable_dependency(self) -> None:
        copy = self.copy_repo()
        path = copy / "workflows/example_workflow/flow.py"
        path.write_text(
            path.read_text()
            .replace(
                "from bricks.example_brick import run as run_example_brick\n",
                "from bricks.example_brick.contract import BrickInput\n",
            )
            .replace("    return run_example_brick(inputs)", "    return BrickInput(**inputs)"),
            encoding="utf-8",
        )
        self.assert_invalid(copy)

    def test_undeclared_import_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        path = copy / "workflows/example_workflow/contract.py"
        path.write_text(path.read_text().replace('("example_brick",)', "()"), encoding="utf-8")
        self.assert_invalid(copy)

    def test_external_effect_is_allowed_only_in_a_brick_adapter(self) -> None:
        copy = self.copy_repo()
        (copy / "bricks/example_brick/input/adapters/source.py").write_text(
            "def read_records():\n    return open('records.json')\n", encoding="utf-8"
        )
        self.regenerate(copy)
        result = self.bend_run("PROOF.bend", cwd=copy)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pure_brick_dependency_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        source = copy / "bricks/example_brick"
        other = copy / "bricks/other"
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
            "from bricks.other import run\n", encoding="utf-8"
        )
        self.assert_invalid(copy)

    def test_pure_brick_external_adapter_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        contract = copy / "bricks/example_brick/contract.py"
        contract.write_text(
            contract.read_text().replace('LANE = "strict"', 'LANE = "pure"'),
            encoding="utf-8",
        )
        (copy / "bricks/example_brick/input/adapters/source.py").write_text(
            "import requests\n", encoding="utf-8"
        )
        self.assert_invalid(copy)

    def test_hidden_input_call_outside_adapter_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        path = copy / "bricks/example_brick/src/logic.py"
        path.write_text(
            path.read_text() + "\nimport random\nrandom.random()\n", encoding="utf-8"
        )
        self.assert_invalid(copy)

    def test_workflow_state_ownership_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        path = copy / "workflows/example_workflow/contract.py"
        path.write_text(path.read_text() + '\nOWNED_STATE = ("db:workflow",)\n', encoding="utf-8")
        self.assert_invalid(copy)

    def test_dependency_cycle_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        source = copy / "bricks/example_brick"
        other = copy / "bricks/other"
        shutil.copytree(source, other)
        example_contract = source / "contract.py"
        other_contract = other / "contract.py"
        example_contract.write_text(
            example_contract.read_text().replace(
                "SIBLING_DEPENDENCIES: dict[str, str] = {}",
                'SIBLING_DEPENDENCIES = {"other": "orchestrated"}',
            ),
            encoding="utf-8",
        )
        other_contract.write_text(
            other_contract.read_text().replace(
                "SIBLING_DEPENDENCIES: dict[str, str] = {}",
                'SIBLING_DEPENDENCIES = {"example_brick": "orchestrated"}',
            ),
            encoding="utf-8",
        )
        (source / "input/adapters/other.py").write_text(
            "from bricks.other import run\n", encoding="utf-8"
        )
        (other / "input/adapters/example.py").write_text(
            "from bricks.example_brick import run\n", encoding="utf-8"
        )
        self.assert_invalid(copy)

    def test_duplicate_state_owner_fails_the_bend_proof(self) -> None:
        copy = self.copy_repo()
        source = copy / "bricks/example_brick"
        other = copy / "bricks/other"
        shutil.copytree(source, other)
        for contract in (source / "contract.py", other / "contract.py"):
            contract.write_text(
                contract.read_text().replace(
                    "OWNED_STATE: tuple[str, ...] = ()", 'OWNED_STATE = ("db:records",)'
                ),
                encoding="utf-8",
            )
        self.assert_invalid(copy)


if __name__ == "__main__":
    unittest.main()
