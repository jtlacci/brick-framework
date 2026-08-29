# Internal Python modules

This repository organizes one codebase as discrete domain modules. Modules are used only by sibling modules inside this repository; they are not external packages or services.

Define every domain as a named folder under `modules/`. `example_module` is an empty placeholder showing the required files and contracts.

```text
modules/<module_name>/
├── __init__.py           # exposes only the internal run entry point
├── AGENTS.md             # module contract
├── input/                # config, adapters, saved data, input contract
├── runner/               # run entry point, IDs, history, tests, runner contract
└── src/                  # private logic and source contract
```

- Add one file under `input/adapters/` for every external source and sibling module.
- Keep external calls out of `src/`.
- Expose only `run` to sibling modules through the module's top-level `__init__.py`.
- Keep recent adapter results under `input/data/` and recent runs under `runner/runs/`.

`modules/__init__.py` enables repository-wide standard-library test discovery. Each module's top-level file defines its repository-internal entry point, while the two under `runner/` and `runner/tests/` give sibling modules' same-named smoke tests distinct import paths. `input/`, `adapters/`, and `src/` do not need package-marker files.

Run all placeholder smoke tests with:

```sh
python3 -m unittest discover -s modules -t . -v
```
