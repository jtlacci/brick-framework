# Domain module contract

Each direct child of `modules/` is one discrete domain module.

Keep `modules/__init__.py` so the standard-library test runner can discover smoke tests across every module from the repository root.

## Required shape

```text
<module_name>/
├── __init__.py
├── AGENTS.md
├── input/
├── runner/
└── src/
```

## Boundaries

- The module's top-level `__init__.py` exports only `run` from `runner/run.py`.
- `runner/` orchestrates the module: it may call adapters and private `src/` logic.
- `input/` owns configuration, external adapters, and saved adapter results.
- `src/` owns private domain logic and performs no I/O.
- Dependency direction is `input <- runner -> src`; `src` never reaches into `input`.
- Another module may be reached only through an adapter that calls the other module's public `run` function.
- Do not import another module's `src/`, `runner/`, configuration, or saved data.

Do not add `__init__.py` merely to mark folders. Keep the repository `modules/` file for discovery, the module-level file for the public API, and the two files under `runner/` and `runner/tests/` for module-qualified test discovery. The other folders use namespace-package behavior.
