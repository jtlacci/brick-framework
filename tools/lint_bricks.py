#!/usr/bin/env python3
"""Check the enforceable brick rules using only the Python standard library."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import sys
from typing import Any


REQUIRED = (
    "__init__.py",
    "contract.py",
    "input/AGENTS.md",
    "input/adapters",
    "input/config.yml",
    "input/data",
    "runner/AGENTS.md",
    "runner/__init__.py",
    "runner/rng.py",
    "runner/run.py",
    "runner/runs",
    "src/AGENTS.md",
)
CONFIG_DEFAULTS = {
    "runs": 10,
    "saved_examples_per_adapter": 3,
    "max_evidence_bytes": 122_880,
    "max_run_record_bytes": 122_880,
}
DIRECT_IO = {
    "boto3", "ftplib", "httpx", "os", "pathlib", "psycopg", "requests",
    "shutil", "smtplib", "socket", "sqlite3", "subprocess", "urllib",
}
SENSITIVE = {
    "access_token", "api_key", "authorization", "client_secret", "cookie", "cookies",
    "headers", "password", "refresh_token", "secret", "set-cookie", "token", "x-api-key",
}


@dataclass
class Contract:
    version: int = 0
    dependencies: dict[str, str] = field(default_factory=dict)
    owned_state: tuple[str, ...] = ()
    lane: str = "strict"


class Lint:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add(self, path: Path, message: str, *, warning: bool = False) -> None:
        try:
            name = path.relative_to(self.root)
        except ValueError:
            name = path
        target = self.warnings if warning else self.errors
        target.append(f"{name}: {message}")

    def tree(self, path: Path) -> ast.Module | None:
        if not path.is_file():
            return None
        try:
            return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            self.add(path, f"cannot parse Python: {exc}")
            return None


def config_number(text: str, key: str, lint: Lint, path: Path) -> int:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(\d+)\s*(?:#.*)?$", text)
    if not match or int(match.group(1)) < 1:
        lint.add(path, f"missing positive integer setting {key!r}")
        return CONFIG_DEFAULTS[key]
    return int(match.group(1))


def imported_modules(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    return ["." * node.level + (node.module or "")]


def called_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def annotation_name(node: ast.expr | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def assigned_literal(tree: ast.Module, name: str) -> Any:
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name:
                value = node.value
        if value is not None:
            try:
                return ast.literal_eval(value)
            except (TypeError, ValueError):
                return None
    return None


def lint_contract(brick: Path, lint: Lint) -> Contract:
    path = brick / "contract.py"
    tree = lint.tree(path)
    if not tree:
        return Contract()

    version = assigned_literal(tree, "CONTRACT_VERSION")
    dependencies = assigned_literal(tree, "SIBLING_DEPENDENCIES")
    owned_state = assigned_literal(tree, "OWNED_STATE")
    lane = assigned_literal(tree, "LANE")
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        lint.add(path, "CONTRACT_VERSION must be a positive integer")
        version = 0
    if not isinstance(dependencies, dict) or not all(
        isinstance(name, str)
        and isinstance(mode, str)
        and mode in {"eventual", "orchestrated"}
        for name, mode in (dependencies.items() if isinstance(dependencies, dict) else ())
    ):
        lint.add(path, "SIBLING_DEPENDENCIES must map names to eventual or orchestrated")
        dependencies = {}
    if not isinstance(owned_state, (tuple, list)) or not all(
        isinstance(item, str) and item for item in owned_state
    ):
        lint.add(path, "OWNED_STATE must contain non-empty resource identifiers")
        owned_state = ()
    for class_name in ("BrickInput", "BrickOutput"):
        declaration = classes.get(class_name)
        if not declaration or not any(annotation_name(base) == "TypedDict" for base in declaration.bases):
            lint.add(path, f"{class_name} must be declared as a TypedDict")
    if lane is None:
        lane = "strict"
    elif lane not in LANES:
        lint.add(path, f"LANE must be one of {', '.join(sorted(LANES))}")
        lane = "strict"

    return Contract(version, dict(dependencies), tuple(owned_state), lane)


def lint_python(brick: Path, contract: Contract, lint: Lint) -> None:
    entry = lint.tree(brick / "__init__.py")
    if entry:
        imports_run = any(
            isinstance(node, ast.ImportFrom)
            and node.level == 1
            and node.module == "runner.run"
            and [name.name for name in node.names] == ["run"]
            for node in entry.body
        )
        exports = None
        for node in entry.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets
            ):
                try:
                    exports = ast.literal_eval(node.value)
                except (TypeError, ValueError):
                    pass
        if not imports_run or exports != ["run"]:
            lint.add(brick / "__init__.py", "must import and export only .runner.run")

    runner = lint.tree(brick / "runner/run.py")
    if runner:
        function = next(
            (node for node in runner.body if isinstance(node, ast.FunctionDef) and node.name == "run"),
            None,
        )
        options = {arg.arg for arg in function.args.kwonlyargs} if function else set()
        if not {"fresh", "save"}.issubset(options):
            lint.add(brick / "runner/run.py", "run needs keyword-only fresh and save options")
        if function:
            input_type = annotation_name(function.args.args[0].annotation) if function.args.args else ""
            if input_type != "BrickInput" or annotation_name(function.returns) != "BrickOutput":
                lint.add(brick / "runner/run.py", "run must use BrickInput and BrickOutput annotations")

    actual_dependencies: set[str] = set()
    for path in brick.rglob("*.py"):
        tree = lint.tree(path)
        if not tree:
            continue
        relative = path.relative_to(brick).parts
        role = relative[0] if len(relative) > 1 else "entry"
        adapter = relative[:2] == ("input", "adapters")
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom):
                    package_depth = len(relative[:-1])
                    if node.level > package_depth + 1:
                        lint.add(path, "relative import may not escape the brick")
                for module in imported_modules(node):
                    parts = module.lstrip(".").split(".")
                    if role == "runner" and "input" in parts:
                        lint.add(path, "runner may not import input")
                    if adapter and ({"src", "runner"} & set(parts)):
                        lint.add(path, "adapter may not import src or runner")
                    if role == "src":
                        if "runner" in parts:
                            lint.add(path, "src may not import runner")
                        if parts[0] in DIRECT_IO:
                            lint.add(path, f"src imports direct-I/O module {parts[0]!r}")
                    if len(parts) > 1 and parts[0] == "bricks" and parts[1] != brick.name:
                        actual_dependencies.add(parts[1])
                        if not adapter:
                            lint.add(path, "only an input adapter may import a sibling brick")
                        elif (
                            not isinstance(node, ast.ImportFrom)
                            or module != f"bricks.{parts[1]}"
                            or [n.name for n in node.names] != ["run"]
                        ):
                            lint.add(path, "sibling adapter may import only run")
                        if parts[1] not in contract.dependencies:
                            lint.add(path, f"sibling dependency {parts[1]!r} is not declared")
            if role == "src" and isinstance(node, ast.Call) and called_name(node) == "open":
                lint.add(path, "src filesystem access must use an adapter")
            if adapter and isinstance(node, ast.Call) and called_name(node) == "run":
                forwarded = {word.arg for word in node.keywords} & {"fresh", "save"}
                if forwarded:
                    lint.add(path, "sibling run may not receive fresh or save")

    for dependency in contract.dependencies.keys() - actual_dependencies:
        lint.add(brick / "contract.py", f"declared dependency {dependency!r} has no static adapter import", warning=True)


def read_json(path: Path, lint: Lint) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        lint.add(path, f"invalid JSON: {exc}")
        return None


def check_secrets(path: Path, value: Any, lint: Lint) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in SENSITIVE and item != "<redacted>":
                lint.add(path, f"sensitive field {key!r} is not redacted")
            check_secrets(path, item, lint)
    elif isinstance(value, list):
        for item in value:
            check_secrets(path, item, lint)


def lint_records(brick: Path, limits: dict[str, int], lint: Lint) -> None:
    data = brick / "input/data"
    counts: dict[str, int] = {}
    for path in sorted(data.rglob("*.json")):
        relative = path.relative_to(data)
        if len(relative.parts) != 2:
            lint.add(path, "evidence path must be <adapter>/<case>.json")
            continue
        adapter, filename = relative.parts
        case = Path(filename).stem
        counts[adapter] = counts.get(adapter, 0) + 1
        if path.stat().st_size > limits["max_evidence_bytes"]:
            lint.add(path, "evidence exceeds max_evidence_bytes")
        record = read_json(path, lint)
        if not isinstance(record, dict):
            continue
        required = {
            "schema_version",
            "contract_version",
            "adapter",
            "case",
            "capture_run_id",
            "request",
        }
        if required - record.keys():
            lint.add(path, "evidence is missing required fields")
        if record.get("adapter") != adapter or record.get("case") != case:
            lint.add(path, "adapter and case must match the path")
        if ("response" in record) == ("error" in record):
            lint.add(path, "evidence needs exactly one of response or error")
        canonical = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode()
        if path.read_bytes() != canonical:
            lint.add(path, "evidence JSON is not canonical")
        check_secrets(path, record, lint)
    for adapter, count in counts.items():
        if count > limits["saved_examples_per_adapter"]:
            lint.add(data / adapter, "too many saved examples")

    runs = sorted((brick / "runner/runs").glob("*.json"))
    if len(runs) > limits["runs"]:
        lint.add(brick / "runner/runs", "too many retained run records")
    for path in runs:
        if path.stat().st_size > limits["max_run_record_bytes"]:
            lint.add(path, "run record exceeds max_run_record_bytes")
        read_json(path, lint)


def lint_smokes(brick: Path, *, top_level: bool, lint: Lint) -> None:
    tests_dir = brick / "runner/tests"
    tests = sorted(tests_dir.glob("test_*.py")) if tests_dir.exists() else []
    if not tests:
        return
    if not (tests_dir / "__init__.py").is_file():
        lint.add(tests_dir / "__init__.py", "smoke-test package marker is missing")
    if tests and not top_level:
        lint.add(tests_dir, "smoke tests belong only to top-level flow bricks")
    if len(tests) > 3:
        lint.add(tests_dir, "top-level flow may have at most three smoke-test files")
    for path in tests:
        tree = lint.tree(path)
        if not tree:
            continue
        if any(
            isinstance(node, ast.Attribute) and node.attr.startswith("skip")
            for node in ast.walk(tree)
        ):
            lint.add(path, "contains a skipped smoke test; it proves no integration", warning=True)
        calls_run = any(
            isinstance(node, ast.Call) and called_name(node) == "run" for node in ast.walk(tree)
        )
        if not calls_run:
            lint.add(path, "smoke test must call the brick's public run")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level:
                lint.add(path, "smoke test must import run from the top-level brick")
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("bricks"):
                if node.module != f"bricks.{brick.name}" or [item.name for item in node.names] != ["run"]:
                    lint.add(path, "smoke test may import only its brick's top-level run")
            if isinstance(node, ast.Import) and any(item.name.startswith("bricks") for item in node.names):
                lint.add(path, "smoke test must use from bricks.<name> import run")


def lint_strict(brick: Path, contract: Contract, lint: Lint) -> None:
    """The regular lane. Every rule above already applies; this adds none."""


PURE_FORBIDDEN = DIRECT_IO | {"random", "time"}
CLOCK_CALLS = {"now", "today", "utcnow"}


def lint_pure(brick: Path, contract: Contract, lint: Lint) -> None:
    """A pure brick's output is a function of its input and nothing else.

    Adapters are the only sanctioned channel to the outside, so a pure brick
    has none, and therefore no sibling dependencies either. The direct-I/O
    ban every ``src/`` already carries widens to the whole brick, joined by
    ``random`` and ``time``, and by the clock calls the ``src/`` contract has
    always forbidden in prose. ``runner/`` is the one exemption: it writes
    run records and owns ``rng.py``, so it keeps the filesystem and
    randomness the rest of the brick gives up. ``datetime`` stays importable:
    arithmetic on a caller-supplied time is pure; reading ``now()`` is not.
    """
    adapters = sorted((brick / "input/adapters").glob("*.py"))
    for path in adapters:
        lint.add(path, "pure brick may not have adapters")
    if contract.dependencies:
        lint.add(brick / "contract.py", "pure brick may not declare sibling dependencies")
    for path in brick.rglob("*.py"):
        relative = path.relative_to(brick).parts
        if relative[0] == "runner":
            continue
        tree = lint.tree(path)
        if not tree:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for module in imported_modules(node):
                    name = module.lstrip(".").split(".")[0]
                    # src/ already reports DIRECT_IO under the rule every brick gets.
                    if name in PURE_FORBIDDEN and not (relative[0] == "src" and name in DIRECT_IO):
                        lint.add(path, f"pure brick imports {name!r} outside runner/")
            if isinstance(node, ast.Call) and called_name(node) in CLOCK_CALLS:
                lint.add(path, f"pure brick reads the clock with {called_name(node)}()")


# A lane is a declared enforcement class: the rules above plus the ones its
# enforcer adds. A lane may only add rules, never relax one (AGENTS.md:
# "may not relax a parent rule"), and it may not exist without an enforcer,
# which is why the table maps each name to a function rather than listing
# names. A contract with no LANE is in the strict lane.
LANES = {
    "strict": lint_strict,
    "pure": lint_pure,
}


def lint_brick(brick: Path, contract: Contract, *, top_level: bool, lint: Lint) -> None:
    for relative in REQUIRED:
        if not (brick / relative).exists():
            lint.add(brick / relative, "required brick path is missing")
    config_path = brick / "input/config.yml"
    config = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    limits = {key: config_number(config, key, lint, config_path) for key in CONFIG_DEFAULTS}
    lint_python(brick, contract, lint)
    lint_records(brick, limits, lint)
    lint_smokes(brick, top_level=top_level, lint=lint)
    LANES[contract.lane](brick, contract, lint)


def lint_graph(
    bricks: list[Path], contracts: dict[str, Contract], lint: Lint
) -> set[str]:
    names = set(contracts)
    incoming: set[str] = set()
    owners: dict[str, str] = {}
    graph: dict[str, set[str]] = {name: set() for name in names}

    for name, contract in contracts.items():
        for dependency in contract.dependencies:
            if dependency == name:
                lint.add(next(brick for brick in bricks if brick.name == name) / "contract.py", "brick may not depend on itself")
            elif dependency not in names:
                lint.add(next(brick for brick in bricks if brick.name == name) / "contract.py", f"unknown sibling dependency {dependency!r}")
            else:
                graph[name].add(dependency)
                incoming.add(dependency)
        for resource in contract.owned_state:
            if resource in owners:
                lint.add(
                    next(brick for brick in bricks if brick.name == name) / "contract.py",
                    f"state {resource!r} is already owned by {owners[resource]!r}",
                )
            else:
                owners[resource] = name

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str, trail: tuple[str, ...]) -> None:
        if name in visiting:
            cycle = " -> ".join((*trail, name))
            lint.add(lint.root / "bricks", f"sibling dependency cycle: {cycle}")
            return
        if name in visited:
            return
        visiting.add(name)
        for dependency in graph[name]:
            visit(dependency, (*trail, name))
        visiting.remove(name)
        visited.add(name)

    for name in sorted(names):
        visit(name, ())
    return names - incoming


def lint_repo(root: Path) -> Lint:
    """Lint every brick under ``root`` and return the findings without printing.

    ``main`` is the command; this is the function a test calls on a fixture tree.
    """
    lint = Lint(root)
    bricks = root / "bricks"
    for path in (root / "AGENTS.md", bricks / "AGENTS.md"):
        if not path.is_file():
            lint.add(path, "required inherited contract is missing")
    for path in root.rglob("BRICK.md"):
        lint.add(path, "contract must be named AGENTS.md")
    if bricks.is_dir():
        brick_paths = sorted(
            path
            for path in bricks.iterdir()
            if path.is_dir() and not path.name.startswith((".", "__"))
        )
        contracts = {brick.name: lint_contract(brick, lint) for brick in brick_paths}
        top_level = lint_graph(brick_paths, contracts, lint)
        for brick in brick_paths:
            lint_brick(
                brick,
                contracts[brick.name],
                top_level=brick.name in top_level,
                lint=lint,
            )
    else:
        lint.add(bricks, "bricks directory is missing")
    return lint


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    lint = lint_repo(parser.parse_args().root.resolve())
    for item in lint.warnings:
        print(f"WARNING {item}")
    for item in lint.errors:
        print(f"ERROR {item}")
    print(f"brick lint {'failed' if lint.errors else 'passed'}: {len(lint.errors)} errors, {len(lint.warnings)} warnings")
    return bool(lint.errors)


if __name__ == "__main__":
    sys.exit(main())
