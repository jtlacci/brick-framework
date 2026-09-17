"""The deterministic half of the review gate: routing, memory, exit rules.

The model half is exercised only in CI. Everything here runs without the
`anthropic` package and without a network.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools import review

ROOT = Path(__file__).resolve().parents[2]


class Fixture(unittest.TestCase):
    """A copy of the boilerplate under a temporary root, one brick per name."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="brick-review-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        shutil.copy(ROOT / "AGENTS.md", self.root / "AGENTS.md")
        (self.root / "bricks").mkdir()
        shutil.copy(ROOT / "bricks/AGENTS.md", self.root / "bricks/AGENTS.md")

    def brick(self, name: str) -> Path:
        target = self.root / "bricks" / name
        shutil.copytree(ROOT / "bricks/example_brick", target,
                        ignore=shutil.ignore_patterns("__pycache__"))
        return target

    def contract(self, brick: Path, **values: str) -> None:
        """Append top-level assignments to the brick's contract."""
        with (brick / "contract.py").open("a", encoding="utf-8") as handle:
            for name, value in values.items():
                handle.write(f"{name} = {value}\n")


class RoutingTests(Fixture):
    def test_brick_of(self) -> None:
        self.assertEqual(review.brick_of("bricks/alpha/src/logic.py"), "alpha")
        self.assertEqual(review.brick_of("bricks/alpha/contract.py"), "alpha")
        self.assertIsNone(review.brick_of("bricks/__init__.py"))
        self.assertIsNone(review.brick_of("bricks/AGENTS.md"))
        self.assertIsNone(review.brick_of("tools/review.py"))
        self.assertIsNone(review.brick_of("README.md"))

    def test_lane_is_read_from_the_contract(self) -> None:
        self.brick("plain")
        self.contract(self.brick("calc"), LANE='"pure"')
        self.contract(self.brick("flow"), LANE='"workflow"')
        self.assertEqual(review.lane_of(self.root, "plain"), "strict")
        self.assertEqual(review.lane_of(self.root, "calc"), "pure")
        self.assertEqual(review.lane_of(self.root, "flow"), "workflow")

    def test_missing_contract_reads_as_strict(self) -> None:
        self.assertEqual(review.lane_of(self.root, "gone"), "strict")

    def test_bad_declaration_reads_as_strict(self) -> None:
        self.contract(self.brick("odd"), LANE='"money"')
        self.contract(self.brick("dyn"), LANE='os.environ["LANE"]')
        (self.brick("broken") / "contract.py").write_text("LANE = (", encoding="utf-8")
        for name in ("odd", "dyn", "broken"):
            self.assertEqual(review.lane_of(self.root, name), "strict", name)

    def test_lanes_are_the_prompts_strict_first(self) -> None:
        self.assertEqual(review.lanes(self.root), ("strict", "pure", "workflow"))

    def test_a_repository_adds_a_lane_by_adding_a_prompt(self) -> None:
        (self.root / "review").mkdir()
        (self.root / "review/money.md").write_text("# money\n", encoding="utf-8")
        (self.root / "review/pure.md").write_text("# our pure\n", encoding="utf-8")
        self.contract(self.brick("desk"), LANE='"money"')
        self.assertEqual(review.lanes(self.root), ("strict", "money", "pure", "workflow"))
        self.assertEqual(review.lane_of(self.root, "desk"), "money")
        # Its own prompt where it has one, the framework's where it does not.
        self.assertEqual(review.prompt_path(self.root, "pure"), self.root / "review/pure.md")
        self.assertEqual(review.prompt_path(self.root, "strict"),
                         review.FRAMEWORK / "review/strict.md")
        self.assertEqual(review.prompt_path(self.root, "common"),
                         review.FRAMEWORK / "review/common.md")

    def test_last_declaration_wins(self) -> None:
        self.contract(self.brick("twice"), LANE='"pure"')
        self.contract(self.root / "bricks/twice", LANE='"workflow"')
        self.assertEqual(review.lane_of(self.root, "twice"), "workflow")

    def test_route_splits_by_lane_and_names_the_rest(self) -> None:
        self.brick("plain")
        self.contract(self.brick("calc"), LANE='"pure"')
        lanes, unrouted = review.route(self.root, [
            "bricks/plain/src/logic.py",
            "bricks/calc/src/logic.py",
            "bricks/calc/contract.py",
            "tools/lint_bricks.py",
            "bricks/AGENTS.md",
        ])
        self.assertEqual(list(lanes), list(review.lanes(self.root)))
        self.assertEqual(lanes["strict"], ["bricks/plain/src/logic.py"])
        self.assertEqual(lanes["pure"], ["bricks/calc/src/logic.py", "bricks/calc/contract.py"])
        self.assertEqual(lanes["workflow"], [])
        self.assertEqual(unrouted, ["tools/lint_bricks.py", "bricks/AGENTS.md"])

    def test_brick_docs_follow_the_touched_bricks(self) -> None:
        self.brick("plain")
        self.brick("other")
        docs = review.brick_docs(self.root, ["bricks/plain/src/logic.py", "bricks/plain/contract.py"])
        self.assertEqual(
            [d.relative_to(self.root).as_posix() for d in docs],
            ["bricks/plain/input/AGENTS.md", "bricks/plain/runner/AGENTS.md", "bricks/plain/src/AGENTS.md"],
        )


class PromptTests(unittest.TestCase):
    def test_every_lane_has_a_prompt(self) -> None:
        # A lane is an enforcer and a prompt. The linter's table is the list.
        self.assertTrue((review.FRAMEWORK / review.PROMPTS / review.COMMON_PROMPT).is_file())
        for lane in review.lanes(ROOT):
            self.assertTrue(review.prompt_path(ROOT, lane).is_file(), lane)

    def test_context_docs_exist(self) -> None:
        for doc in review.CONTEXT_DOCS:
            self.assertTrue((ROOT / doc).is_file(), doc)


class VerdictTests(unittest.TestCase):
    def test_blocks_only_on_a_block_finding(self) -> None:
        advisory = {"file": "x", "issue": "i", "suggestion": "s", "severity": "advisory"}
        block = dict(advisory, severity="block")
        self.assertFalse(review.blocks({"findings": []}))
        self.assertFalse(review.blocks({"findings": [advisory]}))
        self.assertTrue(review.blocks({"findings": [advisory, block]}))


class EnvironmentTests(unittest.TestCase):
    def test_local_run_needs_nothing(self) -> None:
        self.assertIsNone(review.ci_misconfigured({}))

    def test_one_sha_is_an_error_anywhere(self) -> None:
        self.assertIn("both", review.ci_misconfigured({"BASE_SHA": "a"}))

    def test_ci_needs_both_shas(self) -> None:
        self.assertIn("CI", review.ci_misconfigured({"GITHUB_ACTIONS": "true"}))

    def test_ci_needs_a_key(self) -> None:
        message = review.ci_misconfigured(
            {"GITHUB_ACTIONS": "true", "BASE_SHA": "a", "HEAD_SHA": "b"})
        self.assertIn("ANTHROPIC_API_KEY", message)
        self.assertIn("not a review", message)

    def test_ci_fully_configured(self) -> None:
        self.assertIsNone(review.ci_misconfigured(
            {"GITHUB_ACTIONS": "true", "BASE_SHA": "a", "HEAD_SHA": "b",
             "ANTHROPIC_API_KEY": "k"}))

    def test_diff_range(self) -> None:
        self.assertEqual(review.diff_range("a", "b"), ["a...b"])
        self.assertEqual(review.diff_range(None, None), ["HEAD"])


class MemoryTests(Fixture):
    """Carry-forward on a real, tiny repository."""

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def setUp(self) -> None:
        super().setUp()
        self.brick("plain")
        self.git("init", "-q")
        self.first = self.commit("start")

    def test_no_memory_means_full_review(self) -> None:
        self.assertFalse(review.carried_forward(self.root, {}, self.first))

    def test_same_head_is_not_carried(self) -> None:
        previous = {"head": self.first, "lanes": {"strict": {"findings": []}}}
        self.assertFalse(review.carried_forward(self.root, previous, self.first))

    def test_docs_only_delta_carries_forward(self) -> None:
        previous = {"head": self.first, "lanes": {"strict": {"findings": []}}}
        (self.root / "README.md").write_text("notes\n", encoding="utf-8")
        head = self.commit("docs")
        self.assertTrue(review.carried_forward(self.root, previous, head))

    def test_brick_delta_reviews_again(self) -> None:
        previous = {"head": self.first, "lanes": {"strict": {"findings": []}}}
        (self.root / "bricks/plain/src/logic.py").write_text("X = 1\n", encoding="utf-8")
        head = self.commit("logic")
        self.assertFalse(review.carried_forward(self.root, previous, head))

    def test_unknown_sha_reviews_again(self) -> None:
        previous = {"head": "0" * 40, "lanes": {"strict": {"findings": []}}}
        self.assertFalse(review.carried_forward(self.root, previous, self.first))
