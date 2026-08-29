# Domain brick contract

Each direct child of `bricks/` is one discrete domain brick.

Keep `bricks/__init__.py` so the standard-library test runner can discover smoke tests across every brick from the repository root.

## Required shape

```text
<brick_name>/
├── __init__.py
├── BRICK.md
├── input/
├── runner/
└── src/
```

## Boundaries

- The brick's top-level `__init__.py` exposes only the repository-internal `run` entry point from `runner/run.py`.
- `runner/` creates the run context, calls private `src/` logic, and records the run outcome.
- `input/` owns configuration, external-source adapters, sibling adapters, and saved adapter results.
- `src/` owns private domain logic and may call its own `input/` adapters when it needs data or an external effect.
- Execution-call direction is `runner -> src -> input adapter`. `runner` does not call adapters directly, and adapters never call back into `src` or `runner`.
- `runner` passes the caller-supplied brick input unchanged into `src` along with a plain run context containing the run ID, mode, and resolved configuration; `src` passes that context into adapters.
- Each adapter owns saved-versus-fresh behavior and persists its own raw results under its brick's `input/data/` folder.
- `src` may import adapters from its own brick, but it may not directly import external clients or sibling bricks.
- A sibling brick may be reached only through a sibling adapter that calls the sibling's `run` entry point.
- Do not import another brick's `src/`, `runner/`, configuration, or saved data.
- Do not package bricks for, or expose them to, consumers outside this repository.

Do not add `__init__.py` merely to mark folders. Keep the repository `bricks/` file for discovery, the brick-level file for the internal entry point, and the two files under `runner/` and `runner/tests/` for brick-qualified test discovery. The other folders use namespace-package behavior.
