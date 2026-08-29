# Internal Python bricks

This repository organizes one codebase as discrete domain bricks. Bricks are used only by sibling bricks inside this repository; they are not external packages or services.

Define every domain as a named folder under `bricks/`. `example_brick` is an empty placeholder showing the required files and contracts.

```text
bricks/<brick_name>/
├── __init__.py           # exposes only the internal run entry point
├── brick.md             # brick contract
├── input/                # config, adapters, saved data, input contract
├── runner/               # run entry point, IDs, history, tests, runner contract
└── src/                  # private logic and source contract
```

- Add one file under `input/adapters/` for every external source and sibling brick.
- Keep external calls out of `src/`.
- Expose only `run` to sibling bricks through the brick's top-level `__init__.py`.
- Keep recent adapter results under `input/data/` and recent runs under `runner/runs/`.

`bricks/__init__.py` enables repository-wide standard-library test discovery. Each brick's top-level file defines its repository-internal entry point, while the two under `runner/` and `runner/tests/` give sibling bricks' same-named smoke tests distinct import paths. `input/`, `adapters/`, and `src/` do not need package-marker files.

Run all placeholder smoke tests with:

```sh
python3 -m unittest discover -s bricks -t . -v
```
