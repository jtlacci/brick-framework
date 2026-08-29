# Python module boilerplate

This repository is only a folder and file template. It contains no framework runtime.

Copy `modules/example_module`, rename it for the domain, and fill in the TODOs.

```text
modules/<module_name>/
├── input/                # config, adapters, and saved adapter data
├── runner/               # public run entry, run IDs, run history, smoke inputs
└── src/                  # private domain logic
```

- Add one file under `input/adapters/` for every external source, including another module.
- Keep external calls out of `src/`.
- Export only `run` from the module's top-level `__init__.py`.
- Keep recent adapter results under `input/data/` and recent runs under `runner/runs/`.
