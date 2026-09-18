# Brick framework with Bend verification

This repository is language-neutral boilerplate for organizing one codebase into domain **bricks** and application **workflows**. Python demonstrates the host-language shape. Bend does not implement or execute application behavior; it verifies the repository's architecture in CI.

The included extractor understands Python syntax. Supporting another host language means adding a small extractor frontend that emits the same Bend facts; the Bend rules and laws stay unchanged.

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
├── contract.py           # WorkflowInput, WorkflowOutput, brick dependencies
└── flow.py               # translation and brick-call sequencing
```

Bricks own domain behavior, state, and external capabilities. Workflows own whole-use-case composition. A workflow has one input and one output, depends only on bricks, owns no state or infrastructure, and does not call another workflow.

`example_brick` and `example_workflow` are host-language placeholders. Their `NotImplementedError` is intentional: this repository supplies boundaries, not a shared runtime engine.

## Stable Bend verification

The verification path is separate from application code:

```text
tools/model_repository.py   # extracts facts without importing application code
ARCHITECTURE.bend           # generated repository model
verification/rules.bend     # stable framework validation functions
LAWS.bend                   # one stable repository-validity law
PROOF.bend                  # machine-checked proof over generated facts
```

The extractor is the host-language linter and trusted source frontend. It validates local syntax and package shape, interns package and state names as numeric IDs, and records:

- package kind, lane, dependency certificate, and required-shape result;
- cross-package edges and recognizable external-effect imports or calls with their source role and target surface;
- state ownership.

Bend then verifies relationships between those facts: package IDs and state ownership are unique, dependencies target bricks and are acyclic, pure bricks have no dependencies, every declared executable dependency has a public `run` import, cross-package imports use allowed public surfaces, recognizable external effects stay in strict-brick adapters, and workflow state ownership is impossible.

Filesystem and Python-AST facts must be extracted because Bend cannot inspect a repository directly. Bend requires every extractor-defined shape result to be true; it does not independently rediscover those source facts. The generated model is committed, and CI runs the extractor in `--check` mode immediately before Bend so a stale or hand-edited model cannot be proved accidentally.

Static checks identify common effects such as file access, clocks, module-level randomness, system randomness, and UUID generation. They are deliberately conservative rather than a complete purity proof. Semantic review and host-language tests remain responsible for hidden inputs, actual state access, consistency-policy truth, type behavior, and whether a workflow contains only composition.

## What changes when

| Change | Host code | `ARCHITECTURE.bend` | Bend rules/laws |
| --- | --- | --- | --- |
| Brick behavior | Yes | No | No |
| Add or rewire a package | Yes | Regenerate | No |
| Change a framework invariant | Maybe | Regenerate | Yes |

Business laws and example-specific behavior belong in ordinary host-language tests. A normal feature should not edit `LAWS.bend`, `PROOF.bend`, or `verification/rules.bend`.

## Commands

```sh
python3 tools/model_repository.py --write  # after architecture changes
python3 tools/model_repository.py --check  # drift gate
bend PROOF.bend                            # structural proof
python3 tools/graph_bricks.py              # Mermaid dependency graph
python3 -m unittest discover -s tools/tests -t . -v
```

The repository pins Bend in `.bend-version`. Reusable GitHub Actions workflows require an immutable full commit SHA through `framework-ref`, so the extractor and verifier rules cannot drift independently.
