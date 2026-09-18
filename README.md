# Bend brick framework

This repository is Bend 2 boilerplate for a codebase made of domain **bricks** and application **workflows**. Bricks own behavior, state, and external capabilities. Workflows compose brick entry points into whole use cases. Bend supplies typed execution and machine-checked laws; `bend PROOF.bend` is the repository-wide merge gate.

## Structure

```text
bricks/<brick_name>/
├── contract.bend         # BrickInput, BrickOutput, metadata
├── main.bend             # run(input) -> IO(output)
├── laws.bend             # human-owned invariants
├── proof.bend            # machine-checked law implementations
├── input/                # configuration and effect/dependency adapters
├── runner/run.bend       # context and execution handoff
└── src/                  # private domain logic

workflows/<workflow_name>/
├── contract.bend         # WorkflowInput, WorkflowOutput, brick dependencies
├── main.bend             # run(input) -> IO(output)
├── flow.bend             # pure translation and brick-call sequencing
├── laws.bend             # translation/planning invariants
├── proof.bend            # machine-checked law implementations
└── tests/*.bend          # one to three whole-use-case smoke programs
```

`example_brick` is the compiling domain brick. `example_workflow` is the composition example: it sends `21` through `example_brick.run`, translates the returned value, and returns `42`. Both `example.bend` and the workflow smoke program execute that public path.

## Brick contract

Every brick has one typed input, one typed output, and one executable entry:

```bend
def run(input: Contract.BrickInput) -> IO(Contract.BrickOutput):
  Runner.run(input)
```

Its `contract.bend` also declares literal version, lane, sibling dependency, and state-ownership metadata. `Strict{}` is the regular lane. `Pure{}` additionally forbids adapters, sibling dependencies, foreign imports, clocks, files, networking, randomness, and other effects.

Sibling access crosses an input adapter. The adapter may import only the sibling's `contract.bend` types and `main.bend` entry point. A sibling dependency is `Eventual{}` when independent commits and lag are acceptable, or `Orchestrated{}` when the calling brick owns sequencing and compensation. Brick dependency cycles are forbidden, and every persistent state identifier has one owner.

## Workflow contract

Workflows retain the same simple call shape:

```bend
def run(input: Contract.WorkflowInput) -> IO(Contract.WorkflowOutput):
  Flow.run(input)
```

The workflow boundary has exactly one typed `WorkflowInput` and one typed `WorkflowOutput`. `contract.bend` declares a name-only list of bricks:

```bend
def brick_dependencies() -> List<&2, BrickDependency>:
  [BrickDependency{"orders"}, BrickDependency{"inventory"}]
```

“Only brick dependencies” is a capability rule: a workflow may use Bend and its own pure files, but it may not reach a database, API, file, clock, environment, hub package, or foreign implementation directly. Every external capability must enter through a declared brick's public `run`. The linter requires the declared set to exactly match the brick contracts and entries imported by `flow.bend`.

Workflows also may not import other workflows in v1. This keeps the graph one-way and avoids nested application flows. Shared reusable orchestration should be promoted to a domain brick with its own contract.

## What workflow tests do

A workflow has two complementary test layers:

- `laws.bend` and `proof.bend` check pure request translation, result translation, and planning invariants without running effects.
- `tests/*.bend` are compiled smoke programs. They import only the workflow's public contract and `main.bend`, call `run` as a whole, and make the expected use-case result observable. The framework requires one to three, keeping them focused rather than building a second test hierarchy.

Root `LAWS.bend` and `PROOF.bend` aggregate the laws and proofs of every brick and workflow. The linter checks complete custody; reviewers decide whether the laws are sufficient, and Bend verifies their implementations.

## Validation

```sh
bend PROOF.bend
bend bricks/example_brick/main.bend --checkup
bend workflows/example_workflow/main.bend --checkup
bend workflows/example_workflow/tests/smoke.bend
bend example.bend
python3 tools/lint_bricks.py
python3 tools/graph_bricks.py
python3 -m unittest discover -s tools/tests -t . -v
```

The proof command must print `All terms check.` The smoke program and example must print `42`. The linter checks package shape, literal metadata, public signatures, import direction, effect boundaries, ownership, dependency cycles, exact workflow dependency use, and root proof aggregation. The graph command renders workflows above the bricks they compose.

Python remains host-side repository tooling only because Bend 2 does not yet provide the Git, JSON, HTTP/TLS, and subprocess support needed by the optional pull-request review gate. It is not part of brick or workflow runtime behavior.

## Pinned toolchain and reusable CI

The repository pins Bend in `.bend-version`; CI downloads that exact release and verifies its SHA-256. Both reusable workflows require a full commit SHA in `framework-ref`. Callers should pin the workflow `uses:` reference and `framework-ref` to the same immutable revision.
