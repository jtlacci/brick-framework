# Brick framework

This repository is boilerplate for organizing one codebase into domain **bricks** and application **workflows**. Python demonstrates the host-language shape. A deterministic linter and strict host-language typing enforce mechanical boundaries; ordinary tests and semantic review cover behavior and intent.

## Runtime structure

```text
bricks/<brick>/
├── __init__.py           # exposes only run
├── contract.py           # typed input/output and architecture metadata
├── input/
│   ├── adapters/         # external and sibling boundaries
│   ├── data/             # reviewed examples
│   └── config.yml
├── runner/run.py         # one typed executable entry
└── src/                  # private domain logic

workflows/<workflow>/
├── __init__.py           # exposes only run
├── contract.py           # whole-operation input/output and brick dependencies
└── flow.py               # translation and brick-call sequencing
```

Bricks own domain behavior, state, and external capabilities. Workflows own whole-use-case composition. A workflow retains one input and one output, depends only on bricks, owns no state or infrastructure, and does not call another workflow.

`example_brick` and `example_workflow` are placeholders. Their `NotImplementedError` is intentional: this repository supplies boundaries, not a shared runtime engine.

## Enforcement split

`tools/model_repository.py` is the mandatory structural gate. It reads Python syntax and the filesystem without importing application code. It enforces:

- required package shape and typed `run(input) -> output` entries;
- literal contract metadata and known lanes;
- declared, acyclic brick dependencies with actual public `run` imports;
- permitted cross-package surfaces and dependency direction;
- external effects only in strict-brick adapters;
- no dependencies or recognizable effects in pure bricks;
- unique brick state ownership and no workflow-owned state.

The static effect list is conservative, not a complete semantic proof. It recognizes common file, network, process, clock, randomness, secret, and UUID effects and treats unknown libraries as capabilities.

The host-language type gate checks the connections the application actually executes. For the Python frontend, pinned strict mypy checks `bricks/` and `workflows/`. Distinct domain field types make cross-boundary translation explicit, so two structurally similar contracts cannot be connected accidentally. The regression fixture also proves that the configured checker rejects a known-bad connection. This is static enforcement; runtime boundary validation remains application-specific. Other host languages provide an equivalent strict type-checking step.

Business behavior remains the responsibility of ordinary host-language tests. Meaning-level questions—such as whether an adapter is truly thin, a consistency declaration is honest, or a workflow contains domain behavior—remain explicit review responsibilities rather than automated proof claims.

The existing optional Claude review gate remains available for brick changes and is unchanged by this core migration. It routes bricks by lane through `tools/review.py`; top-level `workflows/` remain outside that legacy gate and require human review.

## Commands

```sh
python3 tools/model_repository.py --root . --check
python3 tools/graph_bricks.py
python3 -m unittest discover -s tools/tests -t . -v

# Checks actual Python connections and proves known-bad wiring is rejected.
python3 -m pip install -r requirements-typecheck.txt
python3 -m mypy --config-file mypy.ini bricks workflows
python3 tools/check_typing_fixture.py
```

The reusable GitHub Actions validation workflow requires an immutable full commit SHA through `framework-ref`, so repositories cannot silently switch enforcement versions. Python callers opt into the strict connection gate with `type_check: true`; callers that need third-party type stubs or dependencies can supply a repository-relative `type_check_requirements` file. Missing imports fail rather than degrading boundary types to `Any`.

```yaml
jobs:
  validate:
    uses: jtlacci/brick-framework/.github/workflows/validate.yml@<full-commit-sha>
    with:
      framework-ref: <same-full-commit-sha>
      type_check: true
```

Make the validation check required in branch protection.

Supporting another host language means adding equivalent structural and strict type-checking frontends. The brick/workflow contract does not otherwise depend on Python.
