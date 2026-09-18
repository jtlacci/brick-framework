"""Compile and execute the committed Bend architecture with the pinned toolchain."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
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
            self.assertNotIn("install.sh", text)
            matches = re.findall(r'BEND_SHA256: "([0-9a-f]{64})"', text)
            self.assertEqual(len(matches), 1)
            checksums.update(matches)
        self.assertEqual(len(checksums), 1)

    def test_review_validation_is_unconditional_and_precedes_model_key(self) -> None:
        text = self.workflow("review.yml")
        validation = text.index("- name: validate Bend laws, entries, and boundaries")
        key_gate = text.index("- id: key")
        self.assertLess(validation, key_gate)
        for command in ("bend PROOF.bend", 'bend "$entry" --checkup', "tools/lint_bricks.py"):
            self.assertIn(command, text[validation:key_gate])


class BendIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        requested = os.environ.get("BEND_BIN", "bend")
        cls.bend = shutil.which(requested)
        if cls.bend is None:
            message = f"Bend executable not found: {requested}"
            if os.environ.get("BEND_REQUIRED") == "1":
                raise RuntimeError(message)
            raise unittest.SkipTest(message)

    def bend_run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.bend, *arguments],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def assert_bend_ok(self, *arguments: str) -> str:
        result = self.bend_run(*arguments)
        self.assertEqual(
            result.returncode,
            0,
            f"bend {' '.join(arguments)} failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result.stdout.strip()

    def test_pinned_compiler_version(self) -> None:
        self.assertEqual(self.assert_bend_ok("--version"), f"bend {PINNED_BEND}")

    def test_root_proof_checks_every_brick(self) -> None:
        self.assertEqual(self.assert_bend_ok("PROOF.bend"), "All terms check.")

    def test_every_public_entry_checks_with_its_imports(self) -> None:
        entries = sorted((ROOT / "bricks").glob("*/main.bend"))
        self.assertTrue(entries)
        for entry in entries:
            with self.subTest(entry=entry.relative_to(ROOT)):
                output = self.assert_bend_ok(str(entry.relative_to(ROOT)), "--checkup")
                self.assertIn("All terms check.", output)

    def test_public_composition_executes_across_the_adapter(self) -> None:
        self.assertEqual(self.assert_bend_ok("example.bend"), "42")


if __name__ == "__main__":
    unittest.main()
