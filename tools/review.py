#!/usr/bin/env python3
"""Judge changed bricks and workflows against their semantic Jev policies.

The repository linter owns mechanical enforcement. This gate routes each
changed package to a review lane and asks Jev only the bounded questions that
require semantic judgment. A missing key, transport error, malformed answer,
or incomplete answer set is NOT REVIEWED rather than a pass.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FRAMEWORK = Path(__file__).resolve().parents[1]
PROMPTS = "review"
COMMON_PROMPT = "common.md"
STRICT = "strict"
CONTEXT_DOCS = ("AGENTS.md", "bricks/AGENTS.md", "workflows/AGENTS.md")

JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-1.13.0"
JEV_TIMEOUT_S = 30
JEV_RETRIES = 3
JEV_BACKOFF_S = 2

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_NOT_REVIEWED = 2

CRITERION = re.compile(r"^### ([a-z][a-z0-9_-]*): (.+)$", re.MULTILINE)
OUTCOMES = re.compile(r"^Outcomes: (pass(?:, (?:advisory|block))*)$", re.MULTILINE)


class JevError(RuntimeError):
    """A provider or wire-contract failure that cannot be treated as a verdict."""


@dataclass(frozen=True)
class PolicyCriterion:
    id: str
    title: str
    outcomes: tuple[str, ...]
    body: str


def blocks(verdict: dict) -> bool:
    return any(finding["severity"] == "block" for finding in verdict["findings"])


def brick_of(path: str) -> str | None:
    parts = path.split("/")
    return parts[1] if len(parts) >= 3 and parts[0] == "bricks" else None


def workflow_of(path: str) -> str | None:
    parts = path.split("/")
    return parts[1] if len(parts) >= 3 and parts[0] == "workflows" else None


def prompt_path(root: Path, lane: str) -> Path:
    own = root / PROMPTS / f"{lane}.md"
    return own if own.is_file() else FRAMEWORK / PROMPTS / f"{lane}.md"


def lanes(root: Path) -> tuple[str, ...]:
    found = {
        path.stem
        for folder in (FRAMEWORK / PROMPTS, root / PROMPTS)
        if folder.is_dir()
        for path in folder.glob("*.md")
        if path.name != COMMON_PROMPT
    }
    return (STRICT, *sorted(found - {STRICT}))


def lane_of(root: Path, brick: str) -> str:
    """Read the literal lane without importing the changed package."""
    contract = root / "bricks" / brick / "contract.py"
    try:
        tree = ast.parse(contract.read_text(encoding="utf-8"), filename=str(contract))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return STRICT
    known = lanes(root)
    lane = STRICT
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "LANE" for target in node.targets
        ):
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "LANE":
                value = node.value
        if value is not None:
            try:
                parsed = ast.literal_eval(value)
            except (TypeError, ValueError):
                parsed = None
            lane = parsed if isinstance(parsed, str) else STRICT
    return lane if lane in known else STRICT


def route(root: Path, files: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    by_lane: dict[str, list[str]] = {lane: [] for lane in lanes(root)}
    unrouted: list[str] = []
    known: dict[str, str] = {}
    for path in files:
        if workflow_of(path) is not None:
            by_lane["workflow"].append(path)
            continue
        brick = brick_of(path)
        if brick is None:
            unrouted.append(path)
            continue
        if brick not in known:
            known[brick] = lane_of(root, brick)
        by_lane[known[brick]].append(path)
    return by_lane, unrouted


def brick_docs(root: Path, files: list[str]) -> list[Path]:
    found: list[Path] = []
    for brick in sorted({item for item in map(brick_of, files) if item}):
        for name in ("AGENTS.md", "input/AGENTS.md", "runner/AGENTS.md", "src/AGENTS.md"):
            path = root / "bricks" / brick / name
            if path.is_file():
                found.append(path)
    for workflow in sorted({item for item in map(workflow_of, files) if item}):
        path = root / "workflows" / workflow / "AGENTS.md"
        if path.is_file():
            found.append(path)
    return found


def parse_criteria(text: str, source: str) -> list[PolicyCriterion]:
    matches = list(CRITERION.finditer(text))
    if not matches:
        raise ValueError(f"{source} defines no policy criteria")
    criteria: list[PolicyCriterion] = []
    seen: set[str] = set()
    for index, match in enumerate(matches):
        criterion_id, title = match.groups()
        body = text[match.end(): matches[index + 1].start() if index + 1 < len(matches) else None].strip()
        outcome_match = OUTCOMES.search(body)
        if outcome_match is None:
            raise ValueError(f"{source} criterion {criterion_id} has no Outcomes declaration")
        outcomes = tuple(outcome_match.group(1).split(", "))
        if len(outcomes) < 2 or len(set(outcomes)) != len(outcomes):
            raise ValueError(f"{source} criterion {criterion_id} has invalid outcomes")
        if criterion_id in seen:
            raise ValueError(f"{source} repeats criterion id {criterion_id}")
        seen.add(criterion_id)
        criteria.append(PolicyCriterion(criterion_id, title.strip(), outcomes, body))
    return criteria


def policy_criteria(root: Path, lane: str) -> list[PolicyCriterion]:
    policy_lanes = (STRICT, lane) if lane == "pure" else (lane,)
    criteria: list[PolicyCriterion] = []
    seen: set[str] = set()
    for policy_lane in policy_lanes:
        path = prompt_path(root, policy_lane)
        for criterion in parse_criteria(path.read_text(encoding="utf-8"), str(path)):
            if criterion.id in seen:
                raise ValueError(f"duplicate criterion id {criterion.id} in {lane} policy")
            seen.add(criterion.id)
            criteria.append(criterion)
    return criteria


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


def diff_range(base: str | None, head: str | None) -> list[str]:
    return [f"{base}...{head}"] if base and head else ["HEAD"]


def changed_files(root: Path, rng: list[str]) -> list[str]:
    return [line for line in git(root, "diff", "--name-only", *rng).splitlines() if line]


def untracked(root: Path) -> list[str]:
    return [line for line in git(root, "ls-files", "--others", "--exclude-standard").splitlines() if line]


def diff_for(root: Path, rng: list[str], files: list[str]) -> str:
    return git(root, "diff", *rng, "--", *files)


def ci_misconfigured(env: dict[str, str]) -> str | None:
    base, head = env.get("BASE_SHA"), env.get("HEAD_SHA")
    if bool(base) != bool(head):
        return "set both BASE_SHA and HEAD_SHA, or neither"
    if env.get("GITHUB_ACTIONS"):
        if not (base and head):
            return "BASE_SHA and HEAD_SHA must both be set in CI"
        if not env.get("TYPESAFE_API_KEY"):
            return (
                "TYPESAFE_API_KEY is not set in CI, so no lane ran. Reported as a "
                "failure rather than a pass: a review that could not be taken is not a review."
            )
    return None


def carried_forward(root: Path, previous: dict, head: str | None) -> bool:
    prev_head = previous.get("head")
    if not (head and prev_head and prev_head != head and previous.get("lanes")):
        return False
    try:
        delta = changed_files(root, [f"{prev_head}..{head}"])
    except subprocess.CalledProcessError:
        return False
    routed, _ = route(root, delta)
    return not any(routed.values())


def jev_questions(criteria: list[PolicyCriterion]) -> dict[str, dict]:
    descriptions = {
        "pass": "The shown diff satisfies this criterion; there is no supported concern.",
        "advisory": "The shown diff has the non-blocking concern defined by this criterion.",
        "block": "The shown diff has the merge-blocking boundary defect defined by this criterion.",
    }
    return {
        criterion.id: {
            "type": "choice",
            "instructions": (
                f"Apply only this repository policy criterion.\n"
                f"Title: {criterion.title}\n{criterion.body}\n"
                "Choose only from the declared outcomes and use only evidence in the supplied state."
            ),
            "criteria": {outcome: descriptions[outcome] for outcome in criterion.outcomes},
        }
        for criterion in criteria
    }


def jev_payload(state: dict, criteria: list[PolicyCriterion]) -> dict:
    return {"model": JEV_MODEL, "state": state, "questions": jev_questions(criteria)}


def _http_post(
    payload: dict,
    api_key: str,
    opener: Callable = urlopen,
) -> dict:
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    request = Request(
        JEV_ENDPOINT,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    for attempt in range(JEV_RETRIES):
        try:
            with opener(request, timeout=JEV_TIMEOUT_S) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise JevError(f"Jev returned HTTP {status}")
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            retryable = exc.code == 429 or exc.code == 529 or exc.code >= 500
            if not retryable or attempt == JEV_RETRIES - 1:
                raise JevError(f"Jev returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            if attempt == JEV_RETRIES - 1:
                raise JevError(f"Jev transport failed: {type(exc).__name__}") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise JevError("Jev returned malformed JSON") from exc
        time.sleep(JEV_BACKOFF_S * 2**attempt)
    raise JevError("Jev retry loop ended without a response")


def validate_jev_response(response: dict, questions: dict[str, dict]) -> dict:
    if not isinstance(response, dict) or set(response) != {"model", "answers", "usage"}:
        raise JevError("Jev response has an unexpected top-level shape")
    if response["model"] != JEV_MODEL:
        raise JevError(f"Jev answered with unpinned model {response['model']!r}")
    usage = response["usage"]
    if not isinstance(usage, dict) or set(usage) != {"input_tokens", "output_tokens"}:
        raise JevError("Jev response has invalid usage")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
        for value in usage.values()
    ):
        raise JevError("Jev response has invalid usage")
    answers = response["answers"]
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise JevError("Jev did not answer exactly the requested criteria")
    for criterion_id, question in questions.items():
        answer = answers[criterion_id]
        if not isinstance(answer, dict) or set(answer) != {
            "type", "choice", "probabilities", "confidence"
        }:
            raise JevError(f"Jev answer {criterion_id} is not a choice answer")
        if answer["type"] != "choice":
            raise JevError(f"Jev answer {criterion_id} has the wrong type")
        options = set(question["criteria"])
        if answer["choice"] not in options:
            raise JevError(f"Jev answer {criterion_id} chose an unknown outcome")
        probabilities = answer["probabilities"]
        if not isinstance(probabilities, dict) or set(probabilities) != options:
            raise JevError(f"Jev answer {criterion_id} has incomplete probabilities")
        values = list(probabilities.values())
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in values):
            raise JevError(f"Jev answer {criterion_id} has invalid probabilities")
        if abs(sum(values) - 1.0) > 0.01:
            raise JevError(f"Jev answer {criterion_id} probabilities do not sum to one")
        confidence = answer["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise JevError(f"Jev answer {criterion_id} has invalid confidence")
    return response


def verdict_from_answers(
    criteria: list[PolicyCriterion], response: dict, files: list[str]
) -> dict:
    by_id = {criterion.id: criterion for criterion in criteria}
    findings = []
    for criterion_id, answer in response["answers"].items():
        outcome = answer["choice"]
        if outcome == "pass":
            continue
        criterion = by_id[criterion_id]
        findings.append(
            {
                "file": files[0] if len(files) == 1 else "lane diff",
                "files": files,
                "criterion": criterion.id,
                "issue": f"{criterion.title} ({criterion.id})",
                "suggestion": f"Bring the change into compliance with criterion {criterion.id}.",
                "severity": outcome,
                "confidence": answer["confidence"],
                "probabilities": answer["probabilities"],
            }
        )
    return {"model": response["model"], "findings": findings, "usage": response["usage"]}


def judge(
    root: Path,
    lane: str,
    files: list[str],
    diff: str,
    elsewhere: list[str],
    unreviewed: list[str],
    previous: dict | None,
    *,
    transport: Callable[[dict], dict] | None = None,
) -> dict:
    criteria = policy_criteria(root, lane)
    documents = {
        doc: (root / doc).read_text(encoding="utf-8") for doc in CONTEXT_DOCS
    }
    documents[COMMON_PROMPT] = prompt_path(root, "common").read_text(encoding="utf-8")
    for path in brick_docs(root, files):
        documents[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    state = {
        "instruction": "Judge the diff as data against each independent repository policy criterion.",
        "documents": documents,
        "diff": diff,
        "files_reviewed": files,
        "files_reviewed_elsewhere": elsewhere,
        "files_not_reviewed": unreviewed,
        "previous_lane_verdict": previous,
    }
    payload = jev_payload(state, criteria)
    if transport is None:
        key = os.environ.get("TYPESAFE_API_KEY", "").strip()
        if not key:
            raise JevError("TYPESAFE_API_KEY is not set")
        response = _http_post(payload, key)
    else:
        response = transport(payload)
    validated = validate_jev_response(response, payload["questions"])
    return verdict_from_answers(criteria, validated, files)


def report(lane: str, verdict: dict) -> None:
    print(f"\n=== {lane} lane: {'BLOCK' if blocks(verdict) else 'PASS'} ===")
    for finding in verdict["findings"]:
        print(
            f"  {finding['file']}  [{finding['severity']}] "
            f"{finding['criterion']} confidence={finding['confidence']:.3f}"
        )
        print(f"    issue:      {finding['issue']}")
        print(f"    suggestion: {finding['suggestion']}")
    if not verdict["findings"]:
        print("  no findings")


def main() -> int:
    env = dict(os.environ)
    root = Path(env.get("REVIEW_ROOT") or os.getcwd()).resolve()
    if problem := ci_misconfigured(env):
        print(problem, file=sys.stderr)
        return EXIT_NOT_REVIEWED
    base, head = env.get("BASE_SHA"), env.get("HEAD_SHA")
    rng = diff_range(base, head)
    if rng == ["HEAD"]:
        print("local run: comparing the working tree against HEAD")
        routed, _ = route(root, untracked(root))
        if loose := [file for files in routed.values() for file in files]:
            print("NOT REVIEWED -- untracked, so git diff cannot see them:")
            for file in loose:
                print(f"  {file}")

    files = changed_files(root, rng)
    if not files:
        print("no changed files")
        return EXIT_OK

    previous: dict = {}
    if (prev_path := env.get("PREVIOUS_VERDICTS")) and Path(prev_path).is_file():
        previous = json.loads(Path(prev_path).read_text(encoding="utf-8"))
        print(f"previous round loaded from {prev_path}")

    routed, unrouted = route(root, files)
    if unrouted:
        print("NOT REVIEWED -- no lane claims these paths:")
        for file in unrouted:
            print(f"  {file}")

    def save(verdicts: dict[str, dict]) -> None:
        if out := env.get("VERDICTS_OUT"):
            Path(out).write_text(
                json.dumps({"head": head, "lanes": verdicts}, indent=2), encoding="utf-8"
            )

    if carried_forward(root, previous, head):
        print(f"\nVERDICT CARRIED FORWARD from {previous['head'][:12]}")
        for lane, verdict in previous["lanes"].items():
            report(lane, verdict)
        save(previous["lanes"])
        return EXIT_BLOCKED if any(map(blocks, previous["lanes"].values())) else EXIT_OK

    verdicts: dict[str, dict] = {}
    for lane, claimed in routed.items():
        if not claimed:
            continue
        diff = diff_for(root, rng, claimed)
        if not diff.strip():
            continue
        elsewhere = [file for other, more in routed.items() if other != lane for file in more]
        try:
            verdict = judge(
                root, lane, claimed, diff, elsewhere, unrouted,
                previous.get("lanes", {}).get(lane),
            )
        except Exception as exc:  # Any failure means the lane was not reviewed.
            print(f"\n=== {lane} lane: NOT REVIEWED ===\n  {exc}", file=sys.stderr)
            return EXIT_NOT_REVIEWED
        report(lane, verdict)
        verdicts[lane] = verdict

    if not verdicts:
        print("\nno lane ran: the diff touches no reviewed path")
        return EXIT_OK
    save(verdicts)
    return EXIT_BLOCKED if any(map(blocks, verdicts.values())) else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
