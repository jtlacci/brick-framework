# Domain brick contract

Each direct child of `bricks/` is one discrete domain brick.

Keep `bricks/__init__.py` so the standard-library test runner can discover smoke tests across every brick from the repository root.

## Required shape

```text
<brick_name>/
├── __init__.py
├── brick.md
├── input/
├── runner/
└── src/
```

## Boundaries

- The brick's top-level `__init__.py` exposes only the repository-internal `run` entry point from `runner/run.py`.
- `runner/` orchestrates the brick: it may call adapters and private `src/` logic.
- `input/` owns configuration, external-source adapters, sibling adapters, and saved adapter results.
- `src/` owns private domain logic and performs no I/O.
- Dependency direction is `input <- runner -> src`; `src` never reaches into `input`.
- A sibling brick may be reached only through a sibling adapter that calls the sibling's `run` entry point.
- Do not import another brick's `src/`, `runner/`, configuration, or saved data.
- Do not package bricks for, or expose them to, consumers outside this repository.

Do not add `__init__.py` merely to mark folders. Keep the repository `bricks/` file for discovery, the brick-level file for the internal entry point, and the two files under `runner/` and `runner/tests/` for brick-qualified test discovery. The other folders use namespace-package behavior.
