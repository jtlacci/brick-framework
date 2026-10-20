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

SIBLING_ADAPTER = (
    "from bricks.other import run\n\n\n"
    "def fetch(request, ctx):\n"
    "    return ctx['io'].sibling('other', request, run)\n"
)


class Fixture(unittest.TestCase):
    """A copy of the boilerplate under a temporary root, one brick per name."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="brick-lint-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        shutil.copy(ROOT / "AGENTS.md", self.root / "AGENTS.md")
        (self.root / "bricks").mkdir()
        for name in ("AGENTS.md", "__init__.py", "_runtime.py", "_yaml.py"):
            shutil.copy(ROOT / "bricks" / name, self.root / "bricks" / name)

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

    def policy(self, brick: Path, old: str, new: str) -> None:
        path = brick / "evaluation/policy.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def evaluate(self, brick: Path, old: str, new: str) -> None:
        path = brick / "evaluation/evaluate.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def pure_brick(self, name: str = "example_brick") -> Path:
        """The template with its one adapter removed."""
        brick = self.brick(name)
        (brick / "input/adapters/example_source.py").unlink()
        self.contract(brick, LANE='"pure"')
        return brick

    def errors(self) -> list[str]:
        return lint_bricks.lint_repo(self.root).errors

    def warnings(self) -> list[str]:
        return lint_bricks.lint_repo(self.root).warnings

    def assertError(self, fragment: str) -> None:
        errors = self.errors()
        self.assertTrue(any(fragment in item for item in errors), f"{fragment!r} not in {errors}")

    def assertWarning(self, fragment: str) -> None:
        warnings = self.warnings()
        self.assertTrue(any(fragment in item for item in warnings), f"{fragment!r} not in {warnings}")

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

    def test_framework_runtime_is_required(self) -> None:
        (self.root / "bricks/_runtime.py").unlink()
        self.assertError("bricks/_runtime.py: required framework file is missing")

    def test_src_may_not_import_direct_io(self) -> None:
        brick = self.brick()
        (brick / "src/logic.py").write_text("import requests\n", encoding="utf-8")
        self.assertError("src imports direct-I/O module 'requests'")

    def test_src_may_not_import_http_or_importlib(self) -> None:
        brick = self.brick()
        (brick / "src/logic.py").write_text("import http.client\nimport importlib\n", encoding="utf-8")
        self.assertError("src imports direct-I/O module 'http'")
        self.assertError("src imports direct-I/O module 'importlib'")

    def test_src_may_not_call_dunder_import(self) -> None:
        brick = self.brick()
        (brick / "src/logic.py").write_text("x = __import__('requests')\n", encoding="utf-8")
        self.assertError("src may not call __import__()")

    def test_deterministic_must_be_a_bool(self) -> None:
        self.contract(self.brick(), DETERMINISTIC='"yes"')
        self.assertError("DETERMINISTIC must be True or False")


class SavedModeIsGoneTests(Fixture):
    def test_run_takes_no_mode_options(self) -> None:
        brick = self.brick()
        path = brick / "runner/run.py"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "def run(inputs: BrickInput)", "def run(inputs: BrickInput, *, fresh: bool = False)"
            ),
            encoding="utf-8",
        )
        self.assertError("run takes exactly one argument, the brick input, and no mode options")

    def test_retired_paths_are_rejected(self) -> None:
        brick = self.brick()
        (brick / "input/data").mkdir()
        (brick / "runner/runs").mkdir()
        self.assertError("input/data: retired path")
        self.assertError("runner/runs: retired path")

    def test_unit_and_smoke_tests_are_rejected(self) -> None:
        brick = self.brick()
        (brick / "src/tests").mkdir()
        (brick / "runner/tests").mkdir()
        self.assertError("src/tests: retired path")
        self.assertError("runner/tests: retired path")


class IoRoutingTests(Fixture):
    def two_bricks(self) -> Path:
        self.brick("other")
        brick = self.brick()
        self.contract(brick, SIBLING_DEPENDENCIES='{"other": "eventual"}')
        return brick

    def test_sibling_through_io_lints_clean(self) -> None:
        brick = self.two_bricks()
        (brick / "input/adapters/other.py").write_text(SIBLING_ADAPTER, encoding="utf-8")
        self.assertClean()

    def test_sibling_run_may_not_be_called_directly(self) -> None:
        brick = self.two_bricks()
        (brick / "input/adapters/other.py").write_text(
            "from bricks.other import run\n\n\ndef fetch(request, ctx):\n    return run(request)\n",
            encoding="utf-8",
        )
        self.assertError("call a sibling through ctx['io'].sibling")

    def test_adapter_without_io_warns(self) -> None:
        brick = self.brick()
        (brick / "input/adapters/example_source.py").write_text(
            "def fetch(request, ctx):\n    return {}\n", encoding="utf-8"
        )
        self.assertWarning("adapter makes no call through ctx['io']")

    def test_package_import_of_a_sibling_is_an_error(self) -> None:
        brick = self.two_bricks()
        (brick / "src/logic.py").write_text("from bricks import other\n", encoding="utf-8")
        self.assertError("import a sibling's run as from bricks.<name> import run")

    def test_only_runner_imports_the_runtime(self) -> None:
        brick = self.brick()
        (brick / "src/logic.py").write_text("from bricks import _runtime\n", encoding="utf-8")
        self.assertError("only runner/ may import the framework runtime")

    def test_unknown_framework_module(self) -> None:
        brick = self.brick()
        (brick / "runner/extra.py").write_text("from bricks import _secret\n", encoding="utf-8")
        self.assertError("bricks._secret is not a framework module")


class EvaluationTests(Fixture):
    def test_evaluation_folder_is_required(self) -> None:
        brick = self.brick()
        shutil.rmtree(brick / "evaluation")
        self.assertError("evaluation/evaluate.py: required brick path is missing")

    def test_evaluation_may_not_import_run(self) -> None:
        brick = self.brick()
        self.evaluate(brick, "from ..contract import BrickInput", "from .. import run\nfrom ..contract import BrickInput")
        self.assertError("evaluation/ may import only this brick's contract")

    def test_evaluation_may_not_do_io(self) -> None:
        brick = self.brick()
        self.evaluate(brick, "from ..contract import BrickInput", "import os\nfrom ..contract import BrickInput")
        self.assertError("evaluation imports direct-I/O module 'os'")

    def test_brick_may_not_import_evaluation(self) -> None:
        brick = self.brick()
        (brick / "src/logic.py").write_text("from ..evaluation import evaluate\n", encoding="utf-8")
        self.assertError("only evaluation/ may import evaluation/")

    def test_evaluate_defines_its_functions(self) -> None:
        brick = self.brick()
        self.evaluate(brick, "def generate(", "def make(")
        self.assertError("must define generate()")

    def test_gates_must_be_literal(self) -> None:
        brick = self.brick()
        self.evaluate(brick, "GATES: tuple[tuple[str, str, float], ...] = ()", "GATES = (('score', '==', 1),)")
        self.assertError("GATES must be a literal tuple")

    def test_data_lock_format(self) -> None:
        brick = self.brick()
        (brick / "evaluation/data.lock").write_text("latest\n", encoding="utf-8")
        self.assertError("data.lock must hold")

    def test_data_lock_hash(self) -> None:
        brick = self.brick()
        (brick / "evaluation/data.lock").write_text("sha256:" + "a" * 64 + "\n", encoding="utf-8")
        self.assertClean()

    def test_code_loop_may_not_reach_evaluation(self) -> None:
        brick = self.brick()
        self.policy(brick, "implementation: [src/**", "implementation: [evaluation/**, src/**")
        self.assertError("code_loop surface 'implementation' reaches evaluation/")

    def test_no_surface_may_reach_the_contract(self) -> None:
        brick = self.brick()
        self.policy(brick, "implementation: [src/**", "implementation: [*.py, src/**")
        self.assertError("reaches human-only contract.py")

    def test_loops_may_not_share_a_surface(self) -> None:
        brick = self.brick()
        self.policy(brick, "eval_loop: [evaluation]", "eval_loop: [evaluation, implementation]")
        self.assertError("code_loop and eval_loop may not share a surface")

    def test_split_kind(self) -> None:
        brick = self.brick()
        self.policy(brick, "kind: hash", "kind: random")
        self.assertError("split.kind must be one of hash, time")

    def test_unparseable_policy(self) -> None:
        brick = self.brick()
        (brick / "evaluation/policy.yml").write_text("surfaces: [a, [b]]\n", encoding="utf-8")
        self.assertError("cannot parse policy")


class LaneTests(Fixture):
    def test_absent_lane_is_strict(self) -> None:
        brick = self.brick()
        path = brick / "contract.py"
        kept = [line for line in path.read_text(encoding="utf-8").splitlines(keepends=True)
                if not line.startswith("LANE")]
        path.write_text("".join(kept), encoding="utf-8")
        lint = lint_bricks.lint_repo(self.root)
        self.assertEqual(lint.errors, [])
        self.assertEqual(lint_bricks.lint_contract(brick, lint).lane, "strict")

    def test_every_lane_has_an_enforcer(self) -> None:
        self.assertIn("strict", lint_bricks.LANES)
        for lane, enforcer in lint_bricks.LANES.items():
            self.assertTrue(callable(enforcer), lane)

    def test_unknown_lane_is_an_error(self) -> None:
        self.contract(self.brick(), LANE='"permissive"')
        self.assertError("LANE must be one of")


class PureLaneTests(Fixture):
    def test_pure_brick_lints_clean(self) -> None:
        self.pure_brick()
        self.assertClean()

    def test_template_is_not_pure(self) -> None:
        self.contract(self.brick(), LANE='"pure"')
        self.assertError("pure brick may not have adapters")

    def test_pure_brick_may_not_declare_sibling_dependencies(self) -> None:
        self.brick("other")
        self.contract(self.pure_brick(), SIBLING_DEPENDENCIES='{"other": "eventual"}')
        self.assertError("pure brick may not declare sibling dependencies")

    def test_pure_brick_bans_random_and_time_outside_runner(self) -> None:
        brick = self.pure_brick()
        (brick / "src/helpers.py").write_text("import random\nfrom time import sleep\n", encoding="utf-8")
        self.assertError("pure brick imports 'random' outside runner/")
        self.assertError("pure brick imports 'time' outside runner/")

    def test_pure_brick_evaluation_may_seed_randomness(self) -> None:
        brick = self.pure_brick()
        self.evaluate(brick, "from ..contract import BrickInput", "import random\nfrom ..contract import BrickInput")
        self.assertClean()

    def test_pure_brick_may_not_read_the_clock(self) -> None:
        brick = self.pure_brick()
        (brick / "src/logic.py").write_text(
            "from datetime import datetime\n\n\ndef stamp():\n    return datetime.now()\n",
            encoding="utf-8",
        )
        self.assertError("src/logic.py: pure brick reads the clock with now()")


class WorkflowLaneTests(Fixture):
    def workflow_brick(self, name: str = "example_brick") -> Path:
        brick = self.brick(name)
        self.contract(brick, LANE='"workflow"')
        return brick

    def test_workflow_brick_lints_clean(self) -> None:
        self.workflow_brick()
        self.assertClean()

    def test_nothing_may_depend_on_a_workflow(self) -> None:
        self.workflow_brick("flow")
        self.contract(self.brick("lib"), SIBLING_DEPENDENCIES='{"flow": "eventual"}')
        self.assertError("bricks/lib/contract.py: sibling dependency 'flow' is a workflow brick")

    def test_workflow_may_have_a_process_door(self) -> None:
        brick = self.workflow_brick()
        (brick / "__main__.py").write_text("from . import run\n\nrun({})\n", encoding="utf-8")
        self.assertClean()

    def test_process_door_may_import_only_run(self) -> None:
        brick = self.workflow_brick()
        (brick / "__main__.py").write_text("from .src.logic import execute\n", encoding="utf-8")
        self.assertError("__main__.py: __main__ may import only this brick's run")

    def test_process_door_does_no_direct_io(self) -> None:
        brick = self.workflow_brick()
        (brick / "__main__.py").write_text("import socket\nfrom . import run\n", encoding="utf-8")
        self.assertError("__main__ imports direct-I/O module 'socket'")

    def test_only_a_workflow_has_a_process_door(self) -> None:
        brick = self.brick()
        (brick / "__main__.py").write_text("from . import run\n", encoding="utf-8")
        self.assertError("__main__.py: only a workflow brick may have __main__.py")


WEB_CONTRACT = (
    'CONTRACT_VERSION = 1\nKIND = "web"\nLANE = "strict"\nDETERMINISTIC = True\n'
    "SIBLING_DEPENDENCIES = {}\nOWNED_STATE = ()\n"
)
OBSERVE = "\n\ndef observe(input, browser, base_url):\n    return {}\n"


class WebBrickTests(Fixture):
    def web_brick(self, name: str = "web") -> Path:
        brick = self.root / "bricks" / name
        (brick / "app/src").mkdir(parents=True)
        (brick / "contract.py").write_text(WEB_CONTRACT, encoding="utf-8")
        (brick / "app/AGENTS.md").write_text("# app\n", encoding="utf-8")
        (brick / "app/package.json").write_text('{"name": "web", "scripts": {"build": "node build.js"}}\n')
        (brick / "app/package-lock.json").write_text('{"lockfileVersion": 3, "packages": {"": {}}}\n')
        (brick / "app/src/main.js").write_text("import { get } from './api.js'\nget('/feed')\n")
        (brick / "app/src/api.js").write_text("export const get = (p) => fetch('/api' + p)\n")
        shutil.copytree(ROOT / "bricks/example_brick/evaluation", brick / "evaluation",
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.policy(brick, "implementation: [src/**, input/adapters/**, input/config.yml, runner/**, __main__.py]",
                    "implementation: [app/**]")
        with open(brick / "evaluation/evaluate.py", "a", encoding="utf-8") as handle:
            handle.write(OBSERVE)
        return brick

    def test_a_web_brick_lints_clean(self) -> None:
        self.web_brick()
        self.assertClean()

    def test_a_web_brick_needs_observe(self) -> None:
        brick = self.web_brick()
        self.evaluate(brick, OBSERVE, "\n")
        self.assertError("must define observe()")

    def test_a_web_brick_has_no_python_folders(self) -> None:
        brick = self.web_brick()
        (brick / "src").mkdir()
        self.assertError("a web brick keeps all its code in app/")

    def test_network_calls_only_in_the_api_client(self) -> None:
        brick = self.web_brick()
        (brick / "app/src/feed.js").write_text("fetch('https://example.com/x')\n", encoding="utf-8")
        self.assertError("network calls go only through app/src/api.js")

    def test_no_brick_may_depend_on_a_web_brick(self) -> None:
        self.web_brick()
        other = self.brick("other")
        self.contract(other, SIBLING_DEPENDENCIES='{"web": "eventual"}')
        self.assertError("web is a web brick; no brick may depend on it")

    def test_kind_must_be_known(self) -> None:
        brick = self.web_brick()
        (brick / "contract.py").write_text(WEB_CONTRACT.replace('"web"', '"desktop"'), encoding="utf-8")
        self.assertError("KIND must be one of python, web")


if __name__ == "__main__":
    unittest.main()
