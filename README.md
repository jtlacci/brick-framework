# Python module boilerplate

This repository is only a folder and file template. It contains no framework runtime.

Copy `modules/example_module`, rename it for the domain, and fill in the TODOs.

```text
modules/<module_name>/
├── __init__.py           # exports only run
├── AGENTS.md             # module contract
├── input/                # config, adapters, saved data, input contract
├── runner/               # public run, IDs, history, tests, runner contract
└── src/                  # private logic and source contract
```

- Add one file under `input/adapters/` for every external source, including another module.
- Keep external calls out of `src/`.
- Export only `run` from the module's top-level `__init__.py`.
- Keep recent adapter results under `input/data/` and recent runs under `runner/runs/`.

The top-level module `__init__.py` is intentional because it defines the public API. The other folders use modern Python namespace-package behavior and do not need package-marker files.
