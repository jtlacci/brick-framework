# Domain module contract

Each direct child of `modules/` is one discrete domain module.

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
- Another module may be reached only through an adapter that calls the other module's public `run` function.
- Do not import another module's `src/`, `runner/`, configuration, or saved data.

Do not add `__init__.py` merely to mark folders. The module-level file exists only to define the public API; modern Python can treat the remaining folders as namespace packages.
