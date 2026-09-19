#!/usr/bin/env python3
"""Extract host-language repository facts for the stable Bend verifier."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any


DIRECT_IO = {
    "boto3", "ftplib", "httpx", "os", "pathlib", "psycopg", "requests",
    "shutil", "smtplib", "socket", "sqlite3", "subprocess", "urllib",
}
DYNAMIC_IMPORTS = {"importlib"}
SAFE_MODULES = {
    "__future__",
    "builtins",
    "collections",
    "copy",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "fractions",
    "functools",
    "itertools",
    "json",
    "math",
    "operator",
    "random",
    "re",
    "secrets",
    "statistics",
    "string",
    "time",
    "types",
    "typing",
    "uuid",
}
EXTERNAL_CALLS = {
    "builtins.input",
    "builtins.open",
    "datetime.date.today",
    "datetime.datetime.now",
    "datetime.datetime.today",
    "datetime.datetime.utcnow",
    "input",
    "open",
    "random.betavariate",
    "random.choice",
    "random.choices",
    "random.expovariate",
    "random.gammavariate",
    "random.gauss",
    "random.getrandbits",
    "random.lognormvariate",
    "random.normalvariate",
    "random.paretovariate",
    "random.randbytes",
    "random.randint",
    "random.random",
    "random.randrange",
    "random.sample",
    "random.shuffle",
    "random.triangular",
    "random.uniform",
    "random.vonmisesvariate",
    "random.weibullvariate",
    "time.monotonic",
    "time.monotonic_ns",
    "time.perf_counter",
    "time.perf_counter_ns",
    "time.process_time",
    "time.process_time_ns",
    "time.thread_time",
    "time.thread_time_ns",
    "time.time",
    "time.time_ns",
    "uuid.uuid1",
    "uuid.uuid4",
}
EXTERNAL_CALL_PREFIXES = ("secrets.",)
BRICK_REQUIRED = (
    "__init__.py",
    "contract.py",
    "input/adapters",
    "input/config.yml",
    "input/data",
    "runner/__init__.py",
    "runner/run.py",
    "runner/runs",
    "src/logic.py",
)
WORKFLOW_REQUIRED = ("__init__.py", "contract.py", "flow.py")


@dataclass(frozen=True)
class ImportFact:
    source: str
    target: str | None
    role: str
    surface: str


@dataclass
class PackageFact:
    name: str
    kind: str
    lane: str = "strict"
    dependencies: tuple[str, ...] = ()
    owned_state: tuple[str, ...] = ()
    shape_valid: bool = True
    issues: list[str] = field(default_factory=list)

    def invalidate(self, message: str) -> None:
        self.shape_valid = False
        self.issues.append(message)


@dataclass
class RepositoryModel:
    packages: list[PackageFact]
    imports: list[ImportFact]
    ranks: dict[str, int]


def parse(path: Path, package: PackageFact) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        package.invalidate(f"{path.name}: cannot parse Python: {exc}")
        return None


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


def annotation_name(node: ast.expr | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def typed_dicts(tree: ast.Module) -> set[str]:
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(annotation_name(base) == "TypedDict" for base in node.bases)
    }


def validate_contract(path: Path, package: PackageFact) -> None:
    tree = parse(path, package)
    if tree is None:
        return
    version = assigned_literal(tree, "CONTRACT_VERSION")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        package.invalidate("CONTRACT_VERSION must be a positive integer literal")

    declarations = typed_dicts(tree)
    if package.kind == "brick":
        required = {"BrickInput", "BrickOutput"}
        lane = assigned_literal(tree, "LANE")
        dependencies = assigned_literal(tree, "SIBLING_DEPENDENCIES")
        owned_state = assigned_literal(tree, "OWNED_STATE")
        if lane not in {"strict", "pure"}:
            package.invalidate("LANE must be 'strict' or 'pure'")
        else:
            package.lane = lane
        if not isinstance(dependencies, dict) or not all(
            isinstance(name, str)
            and isinstance(mode, str)
            and mode in {"eventual", "orchestrated"}
            for name, mode in (dependencies.items() if isinstance(dependencies, dict) else ())
        ):
            package.invalidate("SIBLING_DEPENDENCIES must map names to consistency policies")
        else:
            package.dependencies = tuple(sorted(dependencies))
        if not isinstance(owned_state, (tuple, list)) or not all(
            isinstance(item, str) and item for item in owned_state
        ):
            package.invalidate("OWNED_STATE must contain non-empty strings")
        else:
            package.owned_state = tuple(owned_state)
    else:
        required = {"WorkflowInput", "WorkflowOutput"}
        dependencies = assigned_literal(tree, "BRICK_DEPENDENCIES")
        owned_state = assigned_literal(tree, "OWNED_STATE")
        if not isinstance(dependencies, (tuple, list)) or not all(
            isinstance(name, str) and name for name in dependencies
        ):
            package.invalidate("BRICK_DEPENDENCIES must contain brick names")
        elif len(set(dependencies)) != len(dependencies):
            package.invalidate("BRICK_DEPENDENCIES may not contain duplicates")
        else:
            package.dependencies = tuple(dependencies)
        if owned_state is not None:
            if not isinstance(owned_state, (tuple, list)) or not all(
                isinstance(item, str) and item for item in owned_state
            ):
                package.invalidate("workflow OWNED_STATE must contain non-empty strings")
            else:
                package.owned_state = tuple(owned_state)

    for name in sorted(required - declarations):
        package.invalidate(f"contract must declare {name} as a TypedDict")


def exported_run(path: Path, package: PackageFact, module: str) -> None:
    tree = parse(path, package)
    if tree is None:
        return
    imports_run = any(
        isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == module
        and [alias.name for alias in node.names] == ["run"]
        for node in tree.body
    )
    exports = assigned_literal(tree, "__all__")
    if not imports_run or exports != ["run"]:
        package.invalidate(f"{path.name} must import and export only {module}.run")


def run_signature(path: Path, package: PackageFact, input_name: str, output_name: str) -> None:
    tree = parse(path, package)
    if tree is None:
        return
    runs = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "run"
    ]
    if len(runs) != 1 or not isinstance(runs[0], ast.FunctionDef):
        package.invalidate(f"{path.name} must define exactly one synchronous run(inputs)")
        return
    run = runs[0]
    positional = [*run.args.posonlyargs, *run.args.args]
    exact_signature = (
        len(positional) == 1
        and not run.args.defaults
        and run.args.vararg is None
        and not run.args.kwonlyargs
        and run.args.kwarg is None
    )
    if not exact_signature:
        package.invalidate("run must accept exactly one required positional input")
    if run.decorator_list:
        package.invalidate("run may not be decorated")
    if not positional or annotation_name(positional[0].annotation) != input_name:
        package.invalidate(f"run input must be annotated {input_name}")
    if annotation_name(run.returns) != output_name:
        package.invalidate(f"run output must be annotated {output_name}")


def package_role(package: PackageFact, path: Path, root: Path) -> str:
    parts = path.relative_to(root).parts
    if package.kind == "workflow":
        return "flow" if parts == ("flow.py",) else "other"
    return "adapter" if parts[:2] == ("input", "adapters") else "other"


def import_modules(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    return [node.module or ""]


def import_aliases(tree: ast.Module) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".", 1)[0]
                aliases[local] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name != "*":
                    aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return aliases


def qualified_name(node: ast.expr, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        owner = qualified_name(node.value, aliases)
        return f"{owner}.{node.attr}" if owner else node.attr
    return ""


def is_external_call(node: ast.Call, aliases: dict[str, str]) -> bool:
    name = qualified_name(node.func, aliases)
    return name in EXTERNAL_CALLS or name.startswith(EXTERNAL_CALL_PREFIXES)


def resolved_modules(
    node: ast.Import | ast.ImportFrom,
    package: PackageFact,
    path: Path,
    root: Path,
) -> list[str] | None:
    """Return absolute import modules, resolving relative imports from this file."""
    if isinstance(node, ast.Import) or node.level == 0:
        return import_modules(node)

    relative = path.relative_to(root)
    namespace = "bricks" if package.kind == "brick" else "workflows"
    current = [namespace, package.name, *relative.parent.parts]
    if relative.name == "__init__.py":
        current = [namespace, package.name, *relative.parent.parts]
    ascend = node.level - 1
    if ascend >= len(current):
        return None
    base = current[: len(current) - ascend]
    suffix = (node.module or "").split(".") if node.module else []
    return [".".join([*base, *suffix])]


def package_import(
    node: ast.Import | ast.ImportFrom, module: str
) -> tuple[str, str] | None:
    """Return target package and public/internal surface for a cross-package import."""
    parts = module.split(".")
    if len(parts) < 2 or parts[0] not in {"bricks", "workflows"}:
        return None
    target = parts[1]
    if not isinstance(node, ast.ImportFrom):
        return target, "internal"
    names = [alias.name for alias in node.names]
    if len(parts) == 2 and names == ["run"]:
        return target, "entry"
    if len(parts) == 3 and parts[2] == "contract":
        return target, "contract"
    return target, "internal"


def extract_imports(package: PackageFact, root: Path) -> list[ImportFact]:
    facts: list[ImportFact] = []
    for path in sorted(root.rglob("*.py")):
        tree = parse(path, package)
        if tree is None:
            continue
        role = package_role(package, path, root)
        aliases = import_aliases(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {"__import__", "exec"}:
                    package.invalidate(f"{path.name}: dynamic imports cannot be modeled")
                if is_external_call(node, aliases):
                    facts.append(ImportFact(package.name, None, role, "external"))
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            modules = resolved_modules(node, package, path, root)
            if modules is None:
                package.invalidate(f"{path.name}: relative import escapes its package namespace")
                continue
            for module in modules:
                cross = package_import(node, module)
                if cross is not None:
                    target, surface = cross
                    if target != package.name:
                        facts.append(ImportFact(package.name, target, role, surface))
                    continue
                top = module.split(".", 1)[0]
                if top in DYNAMIC_IMPORTS:
                    package.invalidate(f"{path.name}: dynamic imports cannot be modeled")
                    continue
                if top in DIRECT_IO:
                    facts.append(ImportFact(package.name, None, role, "external"))
                elif top not in SAFE_MODULES:
                    # Fail closed: anything not explicitly known to be a pure
                    # library is an external capability and must cross an adapter.
                    facts.append(ImportFact(package.name, None, role, "external"))
    return facts


def package_fact(path: Path, kind: str) -> tuple[PackageFact, list[ImportFact]]:
    package = PackageFact(path.name, kind)
    if list(path.rglob("*.bend")):
        package.invalidate("package behavior may not be implemented in Bend")
    required = BRICK_REQUIRED if kind == "brick" else WORKFLOW_REQUIRED
    for relative in required:
        if not (path / relative).exists():
            package.invalidate(f"missing required path {relative}")
    validate_contract(path / "contract.py", package)
    if kind == "brick":
        exported_run(path / "__init__.py", package, "runner.run")
        run_signature(path / "runner/run.py", package, "BrickInput", "BrickOutput")
    else:
        exported_run(path / "__init__.py", package, "flow")
        run_signature(path / "flow.py", package, "WorkflowInput", "WorkflowOutput")
    return package, extract_imports(package, path)


def dependency_ranks(packages: list[PackageFact]) -> dict[str, int]:
    by_name = {package.name: package for package in packages}
    ranks: dict[str, int] = {}
    visiting: set[str] = set()

    def rank(name: str) -> int:
        if name in ranks:
            return ranks[name]
        if name in visiting:
            ranks[name] = 0
            return 0
        visiting.add(name)
        dependencies = [dep for dep in by_name[name].dependencies if dep in by_name]
        value = 0 if not dependencies else 1 + max(rank(dep) for dep in dependencies)
        visiting.remove(name)
        ranks[name] = value
        return value

    for name in sorted(by_name):
        rank(name)
    return ranks


def build_model(root: Path) -> RepositoryModel:
    packages: list[PackageFact] = []
    imports: list[ImportFact] = []
    for folder, kind in ((root / "bricks", "brick"), (root / "workflows", "workflow")):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_dir() and not path.name.startswith((".", "__")):
                package, found = package_fact(path, kind)
                packages.append(package)
                imports.extend(found)
    packages.sort(key=lambda package: package.name)
    imports.sort(key=lambda item: (item.source, item.target or "", item.role, item.surface))
    return RepositoryModel(packages, imports, dependency_ranks(packages))


def validation_errors(model: RepositoryModel) -> list[str]:
    """Validate the complete repository model without executing application code."""
    errors: list[str] = []
    by_name: dict[str, PackageFact] = {}
    for package in model.packages:
        if package.name in by_name:
            errors.append(f"package name {package.name!r} is used more than once")
        else:
            by_name[package.name] = package
        errors.extend(f"{package.kind} {package.name}: {issue}" for issue in package.issues)

    imports_by_pair = {
        (edge.source, edge.target)
        for edge in model.imports
        if edge.target is not None and edge.surface == "entry"
    }
    for package in model.packages:
        if package.lane == "pure" and package.dependencies:
            errors.append(f"pure brick {package.name}: may not declare dependencies")
        for target_name in package.dependencies:
            target = by_name.get(target_name)
            if target is None:
                errors.append(f"{package.kind} {package.name}: unknown dependency {target_name!r}")
                continue
            if target.kind != "brick":
                errors.append(
                    f"{package.kind} {package.name}: dependency {target_name!r} is not a brick"
                )
            if model.ranks[target_name] >= model.ranks[package.name]:
                errors.append(
                    f"{package.kind} {package.name}: dependency {target_name!r} creates a cycle"
                )
            if (package.name, target_name) not in imports_by_pair:
                errors.append(
                    f"{package.kind} {package.name}: dependency {target_name!r} "
                    "has no public run import"
                )

    for edge in model.imports:
        source = by_name.get(edge.source)
        if source is None:
            errors.append(f"import has unknown source {edge.source!r}")
            continue
        if edge.surface == "external":
            if not (
                source.kind == "brick"
                and source.lane == "strict"
                and edge.role == "adapter"
            ):
                errors.append(
                    f"{source.kind} {source.name}: external capability is allowed only "
                    "in a strict brick adapter"
                )
            continue

        target = by_name.get(edge.target or "")
        if target is None:
            errors.append(
                f"{source.kind} {source.name}: import targets unknown package {edge.target!r}"
            )
            continue
        if target.kind != "brick":
            errors.append(
                f"{source.kind} {source.name}: may import only bricks, not {target.kind} {target.name}"
            )
        if target.name not in source.dependencies:
            errors.append(
                f"{source.kind} {source.name}: import of {target.name!r} is not declared"
            )
        if source.kind == "brick":
            allowed = edge.role == "adapter" and edge.surface == "entry"
        else:
            allowed = edge.role == "flow" and edge.surface in {"entry", "contract"}
        if not allowed:
            errors.append(
                f"{source.kind} {source.name}: {edge.role} may not import "
                f"{edge.surface} surface of {target.name}"
            )

    owners: dict[str, str] = {}
    for package in model.packages:
        if package.kind == "workflow" and package.owned_state:
            errors.append(f"workflow {package.name}: may not own state")
        for resource in package.owned_state:
            if resource in owners:
                errors.append(
                    f"state {resource!r} is owned by both {owners[resource]!r} "
                    f"and {package.name!r}"
                )
            else:
                owners[resource] = package.name
    return errors


def bend_bool(value: bool) -> str:
    return "True{}" if value else "False{}"


def render(model: RepositoryModel) -> str:
    package_ids = {package.name: index for index, package in enumerate(model.packages, 1)}
    resources = sorted({item for package in model.packages for item in package.owned_state})
    resource_ids = {name: index for index, name in enumerate(resources, 1)}
    lines = [
        "# Generated repository facts. Run: python3 tools/model_repository.py --write",
        "import Base",
        "import ./verification/rules.bend as Rules",
        "",
        "# Package ids: " + ", ".join(
            f"{id}={name}" for name, id in package_ids.items()
        ),
        "# State ids: " + (
            ", ".join(f"{id}={name}" for name, id in resource_ids.items()) or "none"
        ),
        "def repository() -> Rules.Repository:",
        "  Rules.Repository{",
        "    [",
    ]
    package_terms: list[str] = []
    for package in model.packages:
        kind = "Brick" if package.kind == "brick" else "Workflow"
        lane = "Pure" if package.lane == "pure" else "Strict"
        dependencies = ", ".join(
            str(package_ids.get(name, 0)) for name in package.dependencies
        )
        package_terms.append(
            "      Rules.Package{"
            f"{package_ids[package.name]}, Rules.{kind}{{}}, Rules.{lane}{{}}, "
            f"{model.ranks[package.name]}, [{dependencies}], {bend_bool(package.shape_valid)}"
            "}"
        )
    lines.append(",\n".join(package_terms))
    lines.extend(["    ],", "    ["])
    import_terms = [
        "      Rules.ImportEdge{"
        f"{package_ids[item.source]}, {package_ids.get(item.target or '', 0)}, "
        f"Rules.{item.role.title()}{{}}, Rules.{item.surface.title()}{{}}"
        "}"
        for item in model.imports
    ]
    lines.append(",\n".join(import_terms))
    lines.extend(["    ],", "    ["])
    state_terms = [
        "      Rules.StateOwner{"
        f"{resource_ids[resource]}, {package_ids[package.name]}"
        "}"
        for package in model.packages
        for resource in package.owned_state
    ]
    lines.append(",\n".join(state_terms))
    lines.extend(["    ]", "  }", ""])
    return "\n".join(lines)


def report_issues(model: RepositoryModel) -> None:
    for package in model.packages:
        for issue in package.issues:
            print(f"MODEL {package.kind} {package.name}: {issue}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true", help="replace ARCHITECTURE.bend")
    action.add_argument("--check", action="store_true", help="fail when the model is stale")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    model = build_model(root)
    output = render(model)
    target = root / "ARCHITECTURE.bend"
    report_issues(model)
    if args.write:
        target.write_text(output, encoding="utf-8")
        return 0
    if args.check:
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        if current != output:
            print("ARCHITECTURE.bend is stale; run python3 tools/model_repository.py --write", file=sys.stderr)
            return 1
        return 0
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
