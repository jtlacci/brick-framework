"""Routing, memory, policy parsing, and Jev wire-contract tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from urllib.error import HTTPError, URLError

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
        (self.root / "workflows").mkdir()
        shutil.copy(ROOT / "workflows/AGENTS.md", self.root / "workflows/AGENTS.md")

    def brick(self, name: str) -> Path:
        target = self.root / "bricks" / name
        shutil.copytree(ROOT / "bricks/example_brick", target,
                        ignore=shutil.ignore_patterns("__pycache__"))
        return target

    def lane(self, brick: Path, constructor: str, *, append: bool = False) -> None:
        path = brick / "contract.py"
        value = constructor.lower()
        if append:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(f"\nLANE = {value!r}\n")
            return
        text = path.read_text(encoding="utf-8")
        text = text.replace('LANE = "strict"', f"LANE = {value!r}")
        path.write_text(text, encoding="utf-8")


class RoutingTests(Fixture):
    def test_brick_of(self) -> None:
        self.assertEqual(review.brick_of("bricks/alpha/src/logic.py"), "alpha")
        self.assertEqual(review.brick_of("bricks/alpha/contract.py"), "alpha")
        self.assertIsNone(review.brick_of("bricks/AGENTS.md"))
        self.assertIsNone(review.brick_of("bricks/AGENTS.md"))
        self.assertIsNone(review.brick_of("tools/review.py"))
        self.assertIsNone(review.brick_of("README.md"))
        self.assertEqual(review.workflow_of("workflows/send_order/flow.py"), "send_order")
        self.assertIsNone(review.workflow_of("workflows/AGENTS.md"))

    def test_lane_is_read_from_the_contract(self) -> None:
        self.brick("plain")
        self.lane(self.brick("calc"), "Pure")
        self.assertEqual(review.lane_of(self.root, "plain"), "strict")
        self.assertEqual(review.lane_of(self.root, "calc"), "pure")

    def test_missing_contract_reads_as_strict(self) -> None:
        self.assertEqual(review.lane_of(self.root, "gone"), "strict")

    def test_bad_declaration_reads_as_strict(self) -> None:
        self.lane(self.brick("odd"), "Money")
        path = self.brick("dyn") / "contract.py"
        path.write_text(path.read_text().replace('LANE = "strict"', "LANE = choose_lane()"), encoding="utf-8")
        (self.brick("broken") / "contract.py").write_text("LANE = ", encoding="utf-8")
        for name in ("odd", "dyn", "broken"):
            self.assertEqual(review.lane_of(self.root, name), "strict", name)

    def test_lanes_are_the_prompts_strict_first(self) -> None:
        self.assertEqual(review.lanes(self.root), ("strict", "pure", "workflow"))

    def test_a_repository_adds_a_lane_by_adding_a_prompt(self) -> None:
        (self.root / "review").mkdir()
        (self.root / "review/money.md").write_text("# money\n", encoding="utf-8")
        (self.root / "review/pure.md").write_text("# our pure\n", encoding="utf-8")
        self.lane(self.brick("desk"), "Money")
        self.assertEqual(review.lanes(self.root), ("strict", "money", "pure", "workflow"))
        self.assertEqual(review.lane_of(self.root, "desk"), "money")
        # Its own prompt where it has one, the framework's where it does not.
        self.assertEqual(review.prompt_path(self.root, "pure"), self.root / "review/pure.md")
        self.assertEqual(review.prompt_path(self.root, "strict"),
                         review.FRAMEWORK / "review/strict.md")
        self.assertEqual(review.prompt_path(self.root, "common"),
                         review.FRAMEWORK / "review/common.md")

    def test_last_declaration_wins(self) -> None:
        (self.root / "review").mkdir()
        (self.root / "review/money.md").write_text("# money\n", encoding="utf-8")
        self.lane(self.brick("twice"), "Pure")
        self.lane(self.root / "bricks/twice", "Money", append=True)
        self.assertEqual(review.lane_of(self.root, "twice"), "money")

    def test_route_splits_by_lane_and_names_the_rest(self) -> None:
        self.brick("plain")
        self.lane(self.brick("calc"), "Pure")
        lanes, unrouted = review.route(self.root, [
            "bricks/plain/src/logic.py",
            "bricks/calc/src/logic.py",
            "bricks/calc/contract.py",
            "workflows/send_order/flow.py",
            "tools/model_repository.py",
            "bricks/AGENTS.md",
        ])
        self.assertEqual(list(lanes), list(review.lanes(self.root)))
        self.assertEqual(lanes["strict"], ["bricks/plain/src/logic.py"])
        self.assertEqual(lanes["pure"], ["bricks/calc/src/logic.py", "bricks/calc/contract.py"])
        self.assertEqual(lanes["workflow"], ["workflows/send_order/flow.py"])
        self.assertEqual(unrouted, ["tools/model_repository.py", "bricks/AGENTS.md"])

    def test_brick_docs_follow_the_touched_bricks(self) -> None:
        brick = self.brick("plain")
        self.brick("other")
        (brick / "AGENTS.md").write_text("# local brick rules\n", encoding="utf-8")
        docs = review.brick_docs(self.root, ["bricks/plain/src/logic.py", "bricks/plain/contract.py"])
        self.assertEqual(
            [d.relative_to(self.root).as_posix() for d in docs],
            ["bricks/plain/AGENTS.md"],
        )

    def test_workflow_docs_follow_a_touched_workflow(self) -> None:
        flow = self.root / "workflows/send_order"
        flow.mkdir()
        (flow / "AGENTS.md").write_text("# local workflow rules\n", encoding="utf-8")
        docs = review.brick_docs(self.root, ["workflows/send_order/flow.py"])
        self.assertEqual(
            [d.relative_to(self.root).as_posix() for d in docs],
            ["workflows/send_order/AGENTS.md"],
        )


class PromptTests(unittest.TestCase):
    def test_every_lane_has_a_prompt(self) -> None:
        # Every derived review profile has a prompt.
        self.assertTrue((review.FRAMEWORK / review.PROMPTS / review.COMMON_PROMPT).is_file())
        for lane in review.lanes(ROOT):
            self.assertTrue(review.prompt_path(ROOT, lane).is_file(), lane)

    def test_context_docs_exist(self) -> None:
        for doc in review.CONTEXT_DOCS:
            self.assertTrue((ROOT / doc).is_file(), doc)

    def test_every_policy_has_unique_stable_criteria(self) -> None:
        expected = {
            "strict": {f"strict-{index}" for index in range(1, 7)},
            "pure": {
                *(f"strict-{index}" for index in range(1, 7)),
                *(f"pure-{index}" for index in range(1, 4)),
            },
            "workflow": {f"workflow-{index}" for index in range(1, 5)},
        }
        for lane, ids in expected.items():
            criteria = review.policy_criteria(ROOT, lane)
            self.assertEqual({criterion.id for criterion in criteria}, ids)
            self.assertEqual(len(criteria), len(ids))

    def test_policy_without_delimited_criteria_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "no policy criteria"):
            review.parse_criteria("# prose only\n", "custom.md")


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
        self.assertIn("AI_GATEWAY_API_KEY", message)
        self.assertIn("not a review", message)

    def test_ci_fully_configured(self) -> None:
        self.assertIsNone(review.ci_misconfigured(
            {"GITHUB_ACTIONS": "true", "BASE_SHA": "a", "HEAD_SHA": "b",
             "AI_GATEWAY_API_KEY": "k"}))

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
        (self.root / "bricks/plain/src/logic.py").write_text("def x():\n    return 1\n", encoding="utf-8")
        head = self.commit("logic")
        self.assertFalse(review.carried_forward(self.root, previous, head))

    def test_unknown_sha_reviews_again(self) -> None:
        previous = {"head": "0" * 40, "lanes": {"strict": {"findings": []}}}
        self.assertFalse(review.carried_forward(self.root, previous, self.first))


class JevContractTests(Fixture):
    @staticmethod
    def response_for(questions: dict, choice: str = "pass") -> dict:
        answers = {}
        for criterion_id, question in questions.items():
            options = list(question["criteria"])
            selected = choice if choice in options else "pass"
            probabilities = {option: 0.0 for option in options}
            probabilities[selected] = 1.0
            answers[criterion_id] = {
                "type": "choice",
                "choice": selected,
                "probabilities": probabilities,
            }
        return {
            "answers": answers,
            "usage": {"inputTokens": 1, "outputTokens": 0},
        }

    def test_question_ids_exactly_match_policy_ids(self) -> None:
        criteria = review.policy_criteria(ROOT, "pure")
        self.assertEqual(set(review.jev_questions(criteria)), {item.id for item in criteria})

    def test_oversized_state_fails_closed_without_truncation(self) -> None:
        criteria = review.policy_criteria(ROOT, "workflow")
        with self.assertRaisesRegex(review.JevError, "Split the pull request"):
            review.jev_payload({"diff": "x" * (review.MAX_STATE_BYTES + 1)}, criteria)

    def test_judge_uses_injected_transport_and_maps_block(self) -> None:
        self.brick("plain")
        seen: list[dict] = []

        def transport(payload: dict) -> dict:
            seen.append(payload)
            return self.response_for(payload["questions"], "block")

        verdict = review.judge(
            self.root,
            "strict",
            ["bricks/plain/src/logic.py"],
            "+ changed domain behavior",
            [],
            [],
            None,
            transport=transport,
        )
        self.assertEqual(
            seen[0]["providerOptions"], {"gateway": {"zeroDataRetention": True}}
        )
        self.assertEqual(set(seen[0]["questions"]), {f"strict-{index}" for index in range(1, 7)})
        self.assertTrue(review.blocks(verdict))
        self.assertTrue(all(item["severity"] == "block" for item in verdict["findings"]))

    def test_response_rejects_unknown_top_level_fields(self) -> None:
        questions = review.jev_questions(review.policy_criteria(ROOT, "workflow"))
        response = self.response_for(questions)
        response["unexpected"] = True
        with self.assertRaisesRegex(review.JevError, "top-level shape"):
            review.validate_jev_response(response, questions)

    def test_response_rejects_bad_probability_distribution(self) -> None:
        questions = review.jev_questions(review.policy_criteria(ROOT, "workflow"))
        response = self.response_for(questions)
        first = next(iter(response["answers"].values()))
        first["probabilities"] = {key: 0.2 for key in first["probabilities"]}
        with self.assertRaisesRegex(review.JevError, "sum to one"):
            review.validate_jev_response(response, questions)

    def test_response_rejects_missing_answer(self) -> None:
        questions = review.jev_questions(review.policy_criteria(ROOT, "workflow"))
        response = self.response_for(questions)
        response["answers"].pop(next(iter(response["answers"])))
        with self.assertRaisesRegex(review.JevError, "exactly the requested"):
            review.validate_jev_response(response, questions)

    def test_response_rejects_unknown_choice(self) -> None:
        questions = review.jev_questions(review.policy_criteria(ROOT, "workflow"))
        response = self.response_for(questions)
        first = next(iter(response["answers"].values()))
        first["choice"] = "invented"
        with self.assertRaisesRegex(review.JevError, "unknown outcome"):
            review.validate_jev_response(response, questions)

    def test_response_accepts_gateway_choice_without_probabilities(self) -> None:
        questions = review.jev_questions(review.policy_criteria(ROOT, "workflow"))
        response = self.response_for(questions)
        for answer in response["answers"].values():
            answer.pop("probabilities")
        self.assertIs(review.validate_jev_response(response, questions), response)

    def test_response_accepts_the_gateway_sdk_fixture_shape(self) -> None:
        questions = review.jev_questions(review.policy_criteria(ROOT, "workflow"))
        response = self.response_for(questions)
        response.update(
            {
                "rounding": {"probabilityDecimals": 2, "scoreDecimals": 2},
                "warnings": [],
                "providerMetadata": {"gateway": {"cost": "0.002"}},
            }
        )
        self.assertIs(review.validate_jev_response(response, questions), response)

    def test_probability_peak_is_reported_as_certainty(self) -> None:
        criteria = review.policy_criteria(ROOT, "workflow")
        questions = review.jev_questions(criteria)
        response = self.response_for(questions, "block")
        verdict = review.verdict_from_answers(
            criteria, response, ["workflows/example_workflow/flow.py"]
        )
        self.assertTrue(verdict["findings"])
        self.assertTrue(all(item["certainty"] == 1.0 for item in verdict["findings"]))

    @unittest.skipUnless(
        os.environ.get("AI_GATEWAY_LIVE_TEST") == "1"
        and bool(os.environ.get("AI_GATEWAY_API_KEY")),
        "set AI_GATEWAY_LIVE_TEST=1 and AI_GATEWAY_API_KEY for a live smoke test",
    )
    def test_live_gateway_smoke(self) -> None:
        criteria = [
            review.PolicyCriterion(
                "smoke-1",
                "The state is a smoke test",
                ("pass", "block"),
                "Outcomes: pass, block\n\nChoose pass for the literal smoke-test state.",
            )
        ]
        payload = review.jev_payload({"text": "This is a smoke test."}, criteria)
        response = review._http_post(payload, os.environ["AI_GATEWAY_API_KEY"])
        review.validate_jev_response(response, payload["questions"])

    def test_http_request_has_pinned_endpoint_body_and_secret_header(self) -> None:
        payload = {
            "state": "x",
            "questions": {"q": {}},
            "providerOptions": {"gateway": {"zeroDataRetention": True}},
        }
        captured = {}

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"ok":true}'

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = request.data
            captured["authorization"] = request.get_header("Authorization")
            captured["content_type"] = request.get_header("Content-type")
            captured["accept"] = request.get_header("Accept")
            captured["protocol"] = request.get_header("Ai-gateway-protocol-version")
            captured["auth_method"] = request.get_header("Ai-gateway-auth-method")
            captured["spec"] = request.get_header("Ai-evaluation-model-specification-version")
            captured["model"] = request.get_header("Ai-model-id")
            captured["timeout"] = timeout
            return Response()

        self.assertEqual(review._http_post(payload, "top-secret", opener), {"ok": True})
        self.assertEqual(captured["url"], review.JEV_ENDPOINT)
        self.assertEqual(captured["authorization"], "Bearer top-secret")
        self.assertEqual(captured["content_type"], "application/json")
        self.assertEqual(captured["accept"], "application/json")
        self.assertEqual(captured["protocol"], review.GATEWAY_PROTOCOL_VERSION)
        self.assertEqual(captured["auth_method"], "api-key")
        self.assertEqual(captured["spec"], review.EVALUATION_SPEC_VERSION)
        self.assertEqual(captured["model"], review.JEV_MODEL)
        self.assertEqual(captured["timeout"], review.JEV_TIMEOUT_S)
        self.assertEqual(
            captured["body"].decode(),
            '{"providerOptions":{"gateway":{"zeroDataRetention":true}},'
            '"questions":{"q":{}},"state":"x"}',
        )

    def test_http_auth_error_fails_closed_without_retry(self) -> None:
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            raise HTTPError(request.full_url, 401, "unauthorized", {}, None)

        with self.assertRaisesRegex(review.JevError, "rotate or reconfigure"):
            review._http_post({}, "secret", opener)
        self.assertEqual(len(calls), 1)

    def test_http_network_error_retries_then_fails_closed(self) -> None:
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            raise URLError("offline")

        with mock.patch("tools.review.time.sleep"):
            with self.assertRaisesRegex(review.JevError, "transport failed"):
                review._http_post({}, "secret", opener)
        self.assertEqual(len(calls), review.JEV_RETRIES)

    def test_http_malformed_json_fails_closed(self) -> None:
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b"not json"

        with self.assertRaisesRegex(review.JevError, "malformed JSON"):
            review._http_post({}, "secret", lambda *_args, **_kwargs: Response())

    def test_missing_key_is_a_nonzero_process_exit_when_a_lane_changed(self) -> None:
        repo = Path(tempfile.mkdtemp(prefix="brick-review-process-"))
        self.addCleanup(shutil.rmtree, repo, ignore_errors=True)
        shutil.copytree(
            ROOT,
            repo,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )

        def git(*args: str) -> None:
            subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

        git("init", "-q")
        git("add", "-A")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "start")
        path = repo / "bricks/example_brick/src/logic.py"
        path.write_text(path.read_text() + "\n# changed\n", encoding="utf-8")
        environment = dict(os.environ)
        environment.pop("AI_GATEWAY_API_KEY", None)
        environment.pop("GITHUB_ACTIONS", None)
        result = subprocess.run(
            ["python3", str(ROOT / "tools/review.py")],
            cwd=repo,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, review.EXIT_NOT_REVIEWED, result.stdout + result.stderr)
        self.assertIn("NOT REVIEWED", result.stderr)
