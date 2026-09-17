# Domain brick contract

Each direct child of `bricks/` is one discrete domain brick. Rules inherit from the repository contract; a brick-level `AGENTS.md` is optional unless that brick adds domain-specific rules.

Keep `bricks/__init__.py` so the standard-library test runner can discover smoke tests across every brick from the repository root.

## Required shape

```text
<brick_name>/
├── __init__.py
├── contract.py
├── input/
│   └── AGENTS.md
├── runner/
│   └── AGENTS.md
└── src/
    └── AGENTS.md
```

## Boundaries

- The brick's top-level `__init__.py` exposes only the repository-internal `run` entry point from `runner/run.py`.
- `contract.py` declares `CONTRACT_VERSION`, typed `BrickInput` and `BrickOutput`, `SIBLING_DEPENDENCIES`, and `OWNED_STATE`. It may also declare `LANE`: `strict` (the default), `pure`, or `workflow`. A lane only adds rules; see the README.
- `contract.py` is not a second public surface. Sibling adapters import only `run`; its annotations carry the boundary types, and the adapter translates into its owning brick's types.
- `SIBLING_DEPENDENCIES` maps each sibling name to `eventual` or `orchestrated`. `eventual` accepts independently committed state and possible lag. `orchestrated` means the importing, dependent brick is responsible for sequencing and compensation; it does not imply a distributed transaction.
- The declared sibling graph must be acyclic. A cycle is a signal to merge responsibilities or introduce a parent brick.
- `OWNED_STATE` lists stable application-resource identifiers. No identifier may be owned by two bricks. Local evidence in `input/data/` and `runner/runs/` does not need to be listed.
- `runner/` creates the run context, calls private `src/` logic, and records the run outcome.
- `input/` owns configuration, external-source adapters, sibling adapters, and saved adapter examples.
- `src/` owns private domain logic and may call its own `input/` adapters when it needs data or an external effect.
- Execution-call direction is `runner -> src -> input adapter`. `runner` does not call adapters directly, and adapters never call back into `src` or `runner`.
- `runner` passes the caller-supplied brick input unchanged into `src` along with a plain run context containing the brick's run ID, mode, and resolved configuration; `src` passes that context into adapters.
- Each adapter owns saved, fresh, and save behavior.
- `src` may import adapters from its own brick, but it may not directly import external clients or sibling bricks.
- A sibling brick may be reached only through a sibling adapter that calls the sibling's `run` entry point.
- Every sibling adapter must correspond to a declared sibling dependency.
- Invocation mode and run identity never propagate across a brick boundary. A sibling adapter calls the sibling `run` with ordinary inputs and no `fresh` or `save` option; the sibling creates its own run ID and uses its default saved mode.
- Do not import another brick's `src/`, `runner/`, configuration, or saved data.
- Do not package bricks for, or expose them to, consumers outside this repository.

Do not add `__init__.py` merely to mark folders. Keep the repository `bricks/` file for discovery, the brick-level file for the internal entry point, and `runner/__init__.py`. Add `runner/tests/__init__.py` only when a `workflow` brick has smoke tests. The other folders use namespace-package behavior.
