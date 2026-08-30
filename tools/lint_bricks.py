#!/usr/bin/env python3
"""Check the enforceable brick rules using only the Python standard library."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import sys
from typing import Any


REQUIRED = (
    "__init__.py",
    "input/AGENTS.md",
    "input/adapters",
    "input/config.yml",
    "input/data",
    "runner/AGENTS.md",
    "runner/__init__.py",
    "runner/rng.py",
    "runner/run.py",
    "runner/runs",
    "runner/tests/__init__.py",
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


def lint_python(brick: Path, lint: Lint) -> None:
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

    for path in brick.rglob("*.py"):
        tree = lint.tree(path)
        if not tree:
            continue
        relative = path.relative_to(brick).parts
        role = relative[0] if len(relative) > 1 else "entry"
        adapter = relative[:2] == ("input", "adapters")
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
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
                        if not adapter:
                            lint.add(path, "only an input adapter may import a sibling brick")
                        elif (
                            not isinstance(node, ast.ImportFrom)
                            or module != f"bricks.{parts[1]}"
                            or [n.name for n in node.names] != ["run"]
                        ):
                            lint.add(path, "sibling adapter may import only run")
            if role == "src" and isinstance(node, ast.Call) and called_name(node) == "open":
                lint.add(path, "src filesystem access must use an adapter")
            if adapter and isinstance(node, ast.Call) and called_name(node) == "run":
                forwarded = {word.arg for word in node.keywords} & {"fresh", "save"}
                if forwarded:
                    lint.add(path, "sibling run may not receive fresh or save")


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
        required = {"schema_version", "adapter", "case", "capture_run_id", "request"}
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


def lint_brick(brick: Path, lint: Lint) -> None:
    for relative in REQUIRED:
        if not (brick / relative).exists():
            lint.add(brick / relative, "required brick path is missing")
    config_path = brick / "input/config.yml"
    config = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    limits = {key: config_number(config, key, lint, config_path) for key in CONFIG_DEFAULTS}
    lint_python(brick, lint)
    lint_records(brick, limits, lint)
    tests = sorted((brick / "runner/tests").glob("test_*.py"))
    if not tests:
        lint.add(brick / "runner/tests", "no smoke tests", warning=True)
    for path in tests:
        tree = lint.tree(path)
        if tree and any(
            isinstance(node, ast.Attribute) and node.attr.startswith("skip")
            for node in ast.walk(tree)
        ):
            lint.add(path, "contains a skipped smoke test; it proves no behavior", warning=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args().root.resolve()
    lint = Lint(root)
    bricks = root / "bricks"
    for path in (root / "AGENTS.md", bricks / "AGENTS.md"):
        if not path.is_file():
            lint.add(path, "required inherited contract is missing")
    for path in root.rglob("BRICK.md"):
        lint.add(path, "contract must be named AGENTS.md")
    if bricks.is_dir():
        for brick in sorted(p for p in bricks.iterdir() if p.is_dir() and not p.name.startswith((".", "__"))):
            lint_brick(brick, lint)
    else:
        lint.add(bricks, "bricks directory is missing")
    for item in lint.warnings:
        print(f"WARNING {item}")
    for item in lint.errors:
        print(f"ERROR {item}")
    print(f"brick lint {'failed' if lint.errors else 'passed'}: {len(lint.errors)} errors, {len(lint.warnings)} warnings")
    return bool(lint.errors)


if __name__ == "__main__":
    sys.exit(main())
