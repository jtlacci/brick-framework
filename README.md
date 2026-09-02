# Internal Python bricks

This repository organizes one codebase as discrete domain bricks. Bricks are used only by sibling bricks inside this repository; they are not external packages or services.

Define every domain as a named folder under `bricks/`. `example_brick` is an empty placeholder showing the required files and contracts.

```text
bricks/<brick_name>/
├── __init__.py           # exposes only the internal run entry point
├── contract.py           # typed boundary, dependencies, state ownership
├── AGENTS.md             # optional domain-specific additions
├── input/                # config, adapters, saved examples, input contract
├── runner/               # run entry point, IDs, history, optional flow smoke tests
└── src/                  # private logic and optional focused tests
```

- Rules inherit from the closest `AGENTS.md`; not every folder needs one. The `input/`, `runner/`, and `src/` folders have contracts because each owns a different boundary.
- Add one file under `input/adapters/` for every external source and sibling brick.
- `src/` reaches external sources and sibling bricks only through its own `input/` adapters.
- Expose only `run` to sibling bricks through the brick's top-level `__init__.py`.
- Keep named adapter examples under `input/data/<adapter>/<case>.json` and recent runs under `runner/runs/`.
- Sibling calls are fully brick-contained: they create their own run IDs and always use their own default saved mode.
- Declare every sibling dependency and its `eventual` or `orchestrated` consistency policy in `contract.py`. The declared graph must be acyclic.
- Declare stable identifiers for application state owned by the brick. One state resource has one owner.

`contract.py` contains:

```python
CONTRACT_VERSION = 1
SIBLING_DEPENDENCIES = {"another_brick": "eventual"}
OWNED_STATE = ("database:example-records",)

class BrickInput(TypedDict): ...
class BrickOutput(TypedDict): ...
```

Smoke tests are not required per brick. Keep them only under `runner/tests/` for the most top-level flows, with at most three files. They prove integration through `run`. Put focused domain tests under `src/tests/` only when the private logic warrants them.

Sibling adapters still import only the sibling's top-level `run`; `contract.py` is not another exported API. The `run` annotations expose the boundary to static tooling, while each adapter translates into its owning brick's types.

Split a brick when `run` becomes a large dispatcher, its adapters stop being easy to understand, or unrelated changes repeatedly touch the same `src/`.

## Saved, fresh, and save

The public Python entry point has the shape:

```python
run(inputs, *, fresh=False, save=False)
```

| Option | Adapter behavior | Tracked example data |
| --- | --- | --- |
| default | Replay the named saved example | Read only |
| `fresh=True` (`--FRESH`) | Call the real source | Unchanged |
| `save=True` (`--SAVE`) | Call the real source, redact and validate it | Atomically replace the named example |

`save=True` implies a fresh call. A missing or mismatched saved example is an error, never an implicit live call. Neither option propagates when a sibling adapter calls another brick.

Examples use stable paths and canonical JSON, so normal runs do not churn Git. An explicit save is the review point that may create a diff. Each saved example includes the capture run ID; run records and evidence can be correlated later without involving the runner in adapter persistence.

`bricks/__init__.py` enables repository-wide standard-library test discovery. Each brick's top-level file defines its repository-internal entry point. Keep `runner/__init__.py`; add `runner/tests/__init__.py` only when that top-level flow has smoke tests. `input/`, `adapters/`, and `src/` do not need package-marker files.

Once at least one top-level flow has a smoke test, run all smoke tests with:

```sh
python3 -m unittest discover -s bricks -t . -v
```

Python's test runner exits with status 5 when no tests exist, which is the expected state of this empty boilerplate.

Check brick shape, import direction, public exports, and evidence limits with:

```sh
python3 tools/lint_bricks.py
```

Render the declared sibling-dependency graph as Mermaid with:

```sh
python3 tools/graph_bricks.py
```

Each node lists the state its brick owns. A solid arrow is an `orchestrated` dependency and a dashed arrow is an `eventual` one. Bricks that no sibling depends on are drawn with a thicker border; those are the top-level flows that may carry smoke tests.
