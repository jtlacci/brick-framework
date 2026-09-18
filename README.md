# Internal Bend bricks

This repository is Bend 2 boilerplate for organizing one codebase as discrete domain bricks. Brick behavior is written in [Bend](https://github.com/bendlang/bend), important invariants are stated in `LAWS.bend`, and `bend PROOF.bend` is the machine-checked merge gate.

Bricks are repository-internal modules, not external packages or services. Define every domain as a named folder under `bricks/`:

```text
bricks/<brick_name>/
├── main.bend             # the only sibling-call surface
├── contract.bend         # typed boundary, lane, dependencies, state ownership
├── AGENTS.md             # optional domain-specific additions
├── input/
│   ├── AGENTS.md
│   ├── config.bend       # typed compile-time configuration
│   └── adapters/         # external and sibling effect boundaries
├── runner/
│   ├── AGENTS.md
│   └── run.bend          # IO orchestration
└── src/
    ├── AGENTS.md
    └── ...               # private domain logic
```

`example_brick` is a compiling reference brick. Its public `run` returns `IO(BrickOutput)`, its private transformation is pure, and the root law proves that the transformation preserves the input value.

## Bend contract

Each `contract.bend` declares `BrickInput`, `BrickOutput`, and four literal metadata definitions:

```bend
def contract_version() -> U32:
  1

def lane() -> Lane:
  Strict{}

def sibling_dependencies() -> List<&2, Dependency>:
  [Dependency{"another_brick", Eventual{}}]

def owned_state() -> List<&2, String>:
  ["database:example-records"]
```

Keep those definitions literal. The host-side linter and graph renderer parse them without executing project code. A dependency is `Eventual{}` when independently committed state and lag are acceptable, or `Orchestrated{}` when the importing brick owns sequencing and compensation. The dependency graph must be acyclic, and every persistent state identifier has one owner.

Sibling adapters import `bricks/<sibling>/contract.bend` for the boundary datatypes and `bricks/<sibling>/main.bend` for execution. Bend modules do not re-export imported constructors, so both imports are required to construct a typed input. Adapters call only `Sibling.run`; they never reach the sibling's runner, source, configuration, or data. The sibling creates its own run context.

Every public brick entry point has this shape:

```bend
def run(input: Contract.BrickInput) -> IO(Contract.BrickOutput):
  Runner.run(input)
```

Using `IO` uniformly keeps pure and effectful bricks composable. Pure bricks return with `IO.pure`; effectful bricks sequence adapters in their runner or source as their local contract requires.

## Laws and proofs

`LAWS.bend` is the human-owned specification. It imports the smallest pure functions needed to state non-negotiable behavior. `PROOF.bend` is the implementation-owned proof and must fill every law. Do not weaken a law to make a proof pass.

After editing Bend code, run:

```sh
bend PROOF.bend
bend bricks/example_brick/main.bend --checkup
bend example.bend
```

The first command must print `All terms check.` The second checks the example entry module and each direct import independently. The third executes the public boundary and prints `42`. Add laws for business invariants, boundary translations, and pure algorithms. IO itself can be constrained by proving equality with an expected IO term, but keep most laws over pure functions so they remain small and useful.

## Lanes

A lane only adds constraints; it never relaxes the base brick boundary.

| Lane | Meaning | Additional enforcement |
| --- | --- | --- |
| `Strict{}` | The regular brick. | None beyond the shared rules. |
| `Pure{}` | Output is a function of input alone. | No adapters, sibling dependencies, foreign imports, clocks, files, networking, randomness, or other effects. The public `run` may only lift a pure result with `IO.pure`. |
| `Workflow{}` | A top-level operation invoked as a whole. | No sibling may depend on it. It alone may define `app.bend` with a process `main`, and may carry up to three Bend smoke programs under `runner/tests/`. |

## Adapters and evidence

Bend 2 intentionally has a small standard library. External adapters may use Base effects or add paired foreign implementations (`effect.c` and `effect.js`) beside the Bend declaration. Keep those foreigns thin: normalization and business decisions stay in Bend.

The previous Python framework's implicit saved/fresh/save JSON runtime is not carried forward. Bend currently has no JSON library, and hiding persistence behind an unproved host runtime would defeat this migration. If a brick needs replayable evidence, model the mode in its typed contract and commit reviewed `.bend` fixture modules under `input/data/`; a live adapter must fail explicitly when its required host effect is unavailable. Fixture capture is an explicit host operation, never an automatic fallback from replay to live data.

## Repository tools

Python remains only as host-side repository tooling because Bend 2 does not yet provide native Git, JSON, HTTP/TLS, or subprocess libraries suitable for the review gate. It is not part of any brick runtime.

```sh
python3 tools/lint_bricks.py
python3 tools/graph_bricks.py
python3 -m unittest discover -s tools/tests -t . -v
```

The linter checks shape, contract literals, import direction, public entry signatures, lane rules, ownership, and graph cycles. The graph command renders declared dependencies as Mermaid. The Python review client remains the transport for the optional model-assisted pull-request review.

## Install Bend

Follow Bend's current upstream instructions, then read the language guide before editing:

```sh
curl -fsSL https://bend-lang.com/install.sh | sh
bend guide
```

Bend 2 is young and its language and tooling may change. This repository currently targets Bend 2.0.5 semantics; CI also exercises the installed release so upstream drift is visible.
