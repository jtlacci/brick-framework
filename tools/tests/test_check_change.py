"""Tests for tools/check_change.py on a throwaway Git repository."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools import check_change, policy

ROOT = Path(__file__).resolve().parents[2]


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


class ChangeCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="brick-change-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        shutil.copytree(ROOT / "bricks/example_brick", self.root / "bricks/demo",
                        ignore=shutil.ignore_patterns("__pycache__"))
        git(self.root, "init", "-q")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
        self.base = git(self.root, "rev-parse", "HEAD").strip()

    def change(self, *paths: str) -> dict:
        for path in paths:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "a", encoding="utf-8") as handle:
                handle.write("\n# changed\n")
        files = check_change.changed_files(self.root, None, None)
        return check_change.classify_change(self.root, self.base, files)

    def test_code_only(self) -> None:
        groups = self.change("bricks/demo/src/logic.py", "bricks/demo/input/adapters/example_source.py")
        self.assertEqual(len(groups[policy.CODE]), 2)
        self.assertEqual(groups[policy.EVALUATION], [])

    def test_evaluation_only(self) -> None:
        groups = self.change("bricks/demo/evaluation/evaluate.py")
        self.assertEqual([p for p, _ in groups[policy.EVALUATION]], ["bricks/demo/evaluation/evaluate.py"])
        self.assertEqual(groups[policy.CODE], [])

    def test_mixed_change_has_both_classes(self) -> None:
        groups = self.change("bricks/demo/src/logic.py", "bricks/demo/evaluation/evaluate.py")
        self.assertTrue(groups[policy.CODE] and groups[policy.EVALUATION])

    def test_human_only_files(self) -> None:
        groups = self.change("bricks/demo/contract.py", "bricks/demo/evaluation/policy.yml", "README.md")
        self.assertEqual(len(groups[policy.HUMAN]), 3)

    def test_a_change_cannot_widen_its_own_permissions(self) -> None:
        # The change moves evaluate.py into the code loop and edits it; the base
        # policy still classifies the edit as evaluation.
        path = self.root / "bricks/demo/evaluation/policy.yml"
        path.write_text(path.read_text().replace("implementation: [src/**", "implementation: [evaluation/evaluate.py, src/**"))
        groups = self.change("bricks/demo/evaluation/evaluate.py")
        self.assertIn("bricks/demo/evaluation/evaluate.py", [p for p, _ in groups[policy.EVALUATION]])

    def test_a_rename_shows_both_paths(self) -> None:
        git(self.root, "mv", "bricks/demo/evaluation/evaluate.py", "bricks/demo/src/evaluate.py")
        git(self.root, "mv", "bricks/demo/contract.py", "bricks/demo/src/contract_copy.py")
        files = check_change.changed_files(self.root, None, None)
        groups = check_change.classify_change(self.root, self.base, files)
        self.assertIn("bricks/demo/evaluation/evaluate.py", [p for p, _ in groups[policy.EVALUATION]])
        self.assertIn("bricks/demo/contract.py", [p for p, _ in groups[policy.HUMAN]])
        self.assertTrue(groups[policy.CODE])

    def test_non_ascii_names_are_classified(self) -> None:
        groups = self.change("bricks/demo/src/données.py")
        self.assertEqual([p for p, _ in groups[policy.CODE]], ["bricks/demo/src/données.py"])

    def test_new_brick_is_human(self) -> None:
        groups = self.change("bricks/fresh/src/logic.py")
        self.assertEqual([p for p, _ in groups[policy.HUMAN]], ["bricks/fresh/src/logic.py"])

    def test_a_removed_brick_is_human(self) -> None:
        shutil.rmtree(self.root / "bricks/demo")
        files = check_change.changed_files(self.root, None, None)
        groups = check_change.classify_change(self.root, self.base, files)
        self.assertEqual(groups[policy.CODE], [])
        self.assertEqual(groups[policy.EVALUATION], [])
        self.assertIn("bricks/demo/contract.py", [p for p, _ in groups[policy.HUMAN]])

    def test_a_removed_brick_is_human_between_commits(self) -> None:
        git(self.root, "rm", "-rq", "bricks/demo")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "remove")
        head = git(self.root, "rev-parse", "HEAD").strip()
        files = check_change.changed_files(self.root, self.base, head)
        groups = check_change.classify_change(self.root, self.base, files, head)
        self.assertEqual((groups[policy.CODE], groups[policy.EVALUATION]), ([], []))

    def test_a_brick_kept_with_one_file_is_not_removed(self) -> None:
        # Deleting all but one file must not turn the code and evaluation files human.
        git(self.root, "rm", "-q", "bricks/demo/src/logic.py", "bricks/demo/evaluation/evaluate.py")
        files = check_change.changed_files(self.root, None, None)
        groups = check_change.classify_change(self.root, self.base, files)
        self.assertTrue(groups[policy.CODE] and groups[policy.EVALUATION])


class PolicyTests(unittest.TestCase):
    def test_template_policy_is_valid(self) -> None:
        loaded = policy.load((ROOT / "bricks/example_brick/evaluation/policy.yml").read_text())
        self.assertEqual(policy.check(loaded), [])

    def test_classify(self) -> None:
        loaded = policy.load((ROOT / "bricks/example_brick/evaluation/policy.yml").read_text())
        self.assertEqual(policy.classify(loaded, "src/a/b.py"), policy.CODE)
        self.assertEqual(policy.classify(loaded, "evaluation/evaluate.py"), policy.EVALUATION)
        self.assertEqual(policy.classify(loaded, "evaluation/data.lock"), policy.HUMAN)
        self.assertEqual(policy.classify(loaded, "contract.py"), policy.HUMAN)
        self.assertEqual(policy.classify(loaded, "AGENTS.md"), policy.HUMAN)


if __name__ == "__main__":
    unittest.main()
