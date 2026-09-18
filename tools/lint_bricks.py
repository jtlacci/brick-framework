#!/usr/bin/env python3
"""Check Bend brick boundaries using only the Python standard library."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import sys


REQUIRED = (
    "main.bend",
    "contract.bend",
    "input/AGENTS.md",
    "input/adapters",
    "input/config.bend",
    "runner/AGENTS.md",
    "runner/run.bend",
    "src/AGENTS.md",
)
LANE_CTORS = {"Strict": "strict", "Pure": "pure", "Workflow": "workflow"}
CONSISTENCY_CTORS = {"Eventual": "eventual", "Orchestrated": "orchestrated"}
IMPORT_RE = re.compile(r"(?m)^\s*import\s+([^\s#]+)(?:\s+as\s+([A-Za-z][\w.]*))?\s*(?:#.*)?$")
DEF_RE = re.compile(r"(?m)^def\s+([A-Za-z][\w.]*)\s*\(")
EFFECT_RE = re.compile(
    r"\b(?:IO\.(?:print|write|print_err|get_env|spawn|sleep|now)|"
    r"Chan\.|File\.|TCP\.|UDP\.|Window\.|Audio\.|App\.)"
)
FOREIGN_RE = re.compile(r'(?m)^\s*import\s+"[^"\n]+\.(?:c|js)"\s*$')
TODO_RE = re.compile(r"\?TODO|\bTODO\b")


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
        (self.warnings if warning else self.errors).append(f"{name}: {message}")

    def text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self.add(path, f"cannot read UTF-8 Bend source: {exc}")
            return ""


def strip_comments(text: str) -> str:
    """Remove Bend line comments; fixture metadata is intentionally literal."""
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def def_body(text: str, name: str) -> str | None:
    """Return an indented definition body without executing Bend source."""
    start = re.search(rf"(?m)^def\s+{re.escape(name)}\s*\([^\n]*\)[^\n]*:\s*$", text)
    if not start:
        return None
    lines: list[str] = []
    for line in text[start.end():].splitlines():
        if line and not line[0].isspace():
            break
        if line.strip():
            lines.append(line.strip())
    return " ".join(lines)


def literal_list(body: str | None) -> list[object] | None:
    if body is None:
        return None
    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, list) else None


def parse_dependencies(body: str | None) -> dict[str, str] | None:
    if body is None:
        return None
    compact = re.sub(r"\s+", "", body)
    if compact == "[]":
        return {}
    if not (compact.startswith("[") and compact.endswith("]")):
        return None
    item_re = re.compile(
        r'Dependency\{"([a-z][a-z0-9_]*)",(Eventual|Orchestrated)\{\}\}'
    )
    items = item_re.findall(compact)
    rebuilt = "[" + ",".join(
        f'Dependency{{"{name}",{ctor}{{}}}}' for name, ctor in items
    ) + "]"
    if rebuilt != compact or len({name for name, _ in items}) != len(items):
        return None
    return {name: CONSISTENCY_CTORS[ctor] for name, ctor in items}


def lint_contract(brick: Path, lint: Lint) -> Contract:
    path = brick / "contract.bend"
    text = strip_comments(lint.text(path)) if path.is_file() else ""
    for type_name in ("Lane", "Consistency", "Dependency", "BrickInput", "BrickOutput"):
        if not re.search(rf"(?m)^type\s+{type_name}\b[^\n]*\bis\s+(?:Data|Type):\s*$", text):
            lint.add(path, f"must declare typed {type_name}")

    version_body = def_body(text, "contract_version")
    version = int(version_body) if version_body and version_body.isdigit() else 0
    if version < 1:
        lint.add(path, "contract_version must return a positive U32 literal")

    lane_body = def_body(text, "lane")
    lane_match = re.fullmatch(r"(Strict|Pure|Workflow)\{\}", lane_body or "")
    lane = LANE_CTORS[lane_match.group(1)] if lane_match else "strict"
    if not lane_match:
        lint.add(path, "lane must return Strict{}, Pure{}, or Workflow{} literally")

    dependencies = parse_dependencies(def_body(text, "sibling_dependencies"))
    if dependencies is None:
        lint.add(
            path,
            'sibling_dependencies must be a literal list of Dependency{"name", Eventual{}|Orchestrated{}}',
        )
        dependencies = {}

    owned_value = literal_list(def_body(text, "owned_state"))
    if owned_value is None or not all(isinstance(item, str) and item for item in owned_value):
        lint.add(path, "owned_state must be a literal list of non-empty strings")
        owned_state: tuple[str, ...] = ()
    else:
        owned_state = tuple(owned_value)

    return Contract(version, dependencies, owned_state, lane)


def bend_imports(path: Path, lint: Lint) -> list[tuple[str, str | None]]:
    return IMPORT_RE.findall(strip_comments(lint.text(path)))


def resolve_import(path: Path, specifier: str) -> Path | None:
    if not specifier.startswith("."):
        return None
    return (path.parent / specifier).resolve()


def role_of(brick: Path, path: Path) -> str:
    relative = path.relative_to(brick).parts
    if len(relative) == 1:
        return "entry"
    if relative[:2] == ("input", "adapters"):
        return "adapter"
    return relative[0]


def lint_entry(brick: Path, lint: Lint) -> None:
    path = brick / "main.bend"
    text = strip_comments(lint.text(path))
    definitions = DEF_RE.findall(text)
    if definitions != ["run"]:
        lint.add(path, "must define only the public run entry point")
    imports = {specifier for specifier, _ in IMPORT_RE.findall(text)}
    expected = {"Base", "./contract.bend", "./runner/run.bend"}
    if imports != expected:
        lint.add(path, "must import only Base, ./contract.bend, and ./runner/run.bend")
    signature = re.compile(
        r"def\s+run\s*\(\s*input\s*:\s*Contract\.BrickInput\s*\)\s*"
        r"->\s*IO\(\s*Contract\.BrickOutput\s*\)\s*:",
        re.MULTILINE,
    )
    if not signature.search(text):
        lint.add(path, "run must accept Contract.BrickInput and return IO(Contract.BrickOutput)")


def lint_sources(brick: Path, contract: Contract, lint: Lint) -> set[str]:
    actual_dependencies: set[str] = set()
    root = lint.root.resolve()
    bricks_root = (lint.root / "bricks").resolve()

    for path in sorted(brick.rglob("*.bend")):
        text = strip_comments(lint.text(path))
        role = role_of(brick, path)
        foreigns: dict[str, set[str]] = {}
        for match in re.finditer(r'(?m)^\s*import\s+"([^"\n]+)\.(c|js)"\s*$', text):
            foreigns.setdefault(match.group(1), set()).add(match.group(2))
        for stem, extensions in foreigns.items():
            if extensions != {"c", "js"}:
                lint.add(path, f"foreign effect {stem!r} needs paired .c and .js implementations")
        if "@unsafe" in text:
            lint.add(path, "@unsafe is forbidden in framework bricks")
        if TODO_RE.search(text):
            lint.add(path, "contains an unresolved TODO")
        if role == "src" and (EFFECT_RE.search(text) or FOREIGN_RE.search(text)):
            lint.add(path, "src performs a direct effect; use an input adapter")

        for specifier, _alias in IMPORT_RE.findall(text):
            if specifier == "Base" or specifier.startswith("0x"):
                if specifier.startswith("0x") and role != "adapter":
                    lint.add(path, "only an input adapter may import a hub package")
                continue
            if specifier.startswith('"') and specifier.endswith('"'):
                foreign = specifier[1:-1]
                if not foreign.endswith((".c", ".js")):
                    lint.add(path, f"unsupported foreign import {foreign!r}")
                elif role != "adapter":
                    lint.add(path, "only an input adapter may declare a foreign effect")
                elif not (path.parent / foreign).is_file():
                    lint.add(path, f"foreign implementation does not exist: {foreign}")
                continue
            target = resolve_import(path, specifier)
            if target is None:
                lint.add(path, f"unsupported import {specifier!r}")
                continue
            if not target.is_file():
                lint.add(path, f"import does not exist: {specifier}")
                continue
            try:
                target.relative_to(root)
            except ValueError:
                lint.add(path, "relative import may not escape the repository")
                continue

            try:
                relative_to_bricks = target.relative_to(bricks_root)
            except ValueError:
                relative_to_bricks = None
            if relative_to_bricks and relative_to_bricks.parts:
                target_brick = relative_to_bricks.parts[0]
                if target_brick != brick.name:
                    actual_dependencies.add(target_brick)
                    if role != "adapter":
                        lint.add(path, "only an input adapter may import a sibling brick")
                    allowed = {
                        bricks_root / target_brick / "main.bend",
                        bricks_root / target_brick / "contract.bend",
                    }
                    if target not in allowed:
                        lint.add(path, "sibling adapter may import only sibling main.bend and contract.bend")
                    if target_brick not in contract.dependencies:
                        lint.add(path, f"sibling dependency {target_brick!r} is not declared")
                    continue

            try:
                local_parts = target.relative_to(brick.resolve()).parts
            except ValueError:
                local_parts = ()
            if role == "runner" and local_parts[:2] == ("input", "adapters"):
                lint.add(path, "runner may not import input adapters")
            if role == "adapter" and local_parts and local_parts[0] in {"src", "runner"}:
                lint.add(path, "adapter may not import src or runner")
            if role == "src" and local_parts and local_parts[0] == "runner":
                lint.add(path, "src may not import runner")

    for dependency in contract.dependencies.keys() - actual_dependencies:
        lint.add(
            brick / "contract.bend",
            f"declared dependency {dependency!r} has no static adapter import",
            warning=True,
        )
    return actual_dependencies


def lint_runner(brick: Path, lint: Lint) -> None:
    path = brick / "runner/run.bend"
    text = strip_comments(lint.text(path))
    signature = re.compile(
        r"def\s+run\s*\(\s*input\s*:\s*Contract\.BrickInput\s*\)\s*"
        r"->\s*IO\(\s*Contract\.BrickOutput\s*\)\s*:",
        re.MULTILINE,
    )
    if not signature.search(text):
        lint.add(path, "runner run must use the contract input and IO output types")


def lint_smokes(brick: Path, contract: Contract, lint: Lint) -> None:
    tests = sorted((brick / "runner/tests").glob("*.bend"))
    if not tests:
        return
    if contract.lane != "workflow":
        lint.add(brick / "runner/tests", "smoke programs belong only to workflow bricks")
    if len(tests) > 3:
        lint.add(brick / "runner/tests", "a workflow may have at most three smoke programs")
    for path in tests:
        text = strip_comments(lint.text(path))
        if not re.search(r"(?m)^def\s+main\s*\(", text):
            lint.add(path, "smoke program must define main")
        imports = [specifier for specifier, _ in IMPORT_RE.findall(text) if specifier != "Base"]
        if imports != ["../../main.bend"]:
            lint.add(path, "smoke program may import only ../../main.bend besides Base")


def lint_strict(brick: Path, contract: Contract, lint: Lint) -> None:
    """The regular lane adds no rules beyond the shared boundary."""


def lint_pure(brick: Path, contract: Contract, lint: Lint) -> None:
    for path in sorted((brick / "input/adapters").glob("*.bend")):
        lint.add(path, "pure brick may not have adapters")
    if contract.dependencies:
        lint.add(brick / "contract.bend", "pure brick may not declare sibling dependencies")
    for path in sorted(brick.rglob("*.bend")):
        text = strip_comments(lint.text(path))
        if EFFECT_RE.search(text) or FOREIGN_RE.search(text):
            lint.add(path, "pure brick may not perform effects")


def lint_workflow(brick: Path, contract: Contract, lint: Lint) -> None:
    app = brick / "app.bend"
    if not app.exists():
        return
    text = strip_comments(lint.text(app))
    imports = [specifier for specifier, _ in IMPORT_RE.findall(text) if specifier != "Base"]
    if imports != ["./main.bend"]:
        lint.add(app, "app.bend may import only ./main.bend besides Base")
    if not re.search(r"(?m)^def\s+main\s*\(", text):
        lint.add(app, "app.bend must define the workflow process main")


LANES = {"strict": lint_strict, "pure": lint_pure, "workflow": lint_workflow}


def lint_brick(brick: Path, contract: Contract, lint: Lint) -> None:
    for relative in REQUIRED:
        if not (brick / relative).exists():
            lint.add(brick / relative, "required brick path is missing")
    for path in brick.rglob("*.py"):
        lint.add(path, "Python runtime code is not allowed inside a Bend brick")
    lint_entry(brick, lint)
    lint_runner(brick, lint)
    lint_sources(brick, contract, lint)
    lint_smokes(brick, contract, lint)
    if contract.lane != "workflow" and (brick / "app.bend").exists():
        lint.add(brick / "app.bend", "only a workflow brick may have app.bend")
    LANES[contract.lane](brick, contract, lint)


def lint_graph(bricks: list[Path], contracts: dict[str, Contract], lint: Lint) -> None:
    names = set(contracts)
    owners: dict[str, str] = {}
    graph: dict[str, set[str]] = {name: set() for name in names}
    paths = {brick.name: brick / "contract.bend" for brick in bricks}

    for name, contract in contracts.items():
        for dependency in contract.dependencies:
            if dependency == name:
                lint.add(paths[name], "brick may not depend on itself")
            elif dependency not in names:
                lint.add(paths[name], f"unknown sibling dependency {dependency!r}")
            else:
                if contracts[dependency].lane == "workflow":
                    lint.add(
                        paths[name],
                        f"sibling dependency {dependency!r} is a workflow brick",
                    )
                graph[name].add(dependency)
        for resource in contract.owned_state:
            if resource in owners:
                lint.add(paths[name], f"state {resource!r} is already owned by {owners[resource]!r}")
            else:
                owners[resource] = name

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str, trail: tuple[str, ...]) -> None:
        if name in visiting:
            lint.add(lint.root / "bricks", f"sibling dependency cycle: {' -> '.join((*trail, name))}")
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


def lint_repo(root: Path) -> Lint:
    """Lint every brick under root and return findings without printing."""
    lint = Lint(root)
    bricks_dir = root / "bricks"
    for path in (root / "AGENTS.md", root / "LAWS.bend", root / "PROOF.bend", bricks_dir / "AGENTS.md"):
        if not path.is_file():
            lint.add(path, "required repository contract is missing")
    if not bricks_dir.is_dir():
        lint.add(bricks_dir, "bricks directory is missing")
        return lint
    bricks = sorted(
        path for path in bricks_dir.iterdir()
        if path.is_dir() and not path.name.startswith((".", "__"))
    )
    contracts = {brick.name: lint_contract(brick, lint) for brick in bricks}
    lint_graph(bricks, contracts, lint)
    for brick in bricks:
        lint_brick(brick, contracts[brick.name], lint)
    return lint


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    lint = lint_repo(parser.parse_args().root.resolve())
    for item in lint.warnings:
        print(f"WARNING {item}")
    for item in lint.errors:
        print(f"ERROR {item}")
    print(
        f"brick lint {'failed' if lint.errors else 'passed'}: "
        f"{len(lint.errors)} errors, {len(lint.warnings)} warnings"
    )
    return bool(lint.errors)


if __name__ == "__main__":
    sys.exit(main())
