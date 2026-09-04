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
LANE = "strict"
SIBLING_DEPENDENCIES = {"another_brick": "eventual"}
OWNED_STATE = ("database:example-records",)

class BrickInput(TypedDict): ...
class BrickOutput(TypedDict): ...
```

Smoke tests are not required per brick. Keep them only under `runner/tests/` of a `workflow` brick, with at most three files. They prove integration through `run`. Put focused domain tests under `src/tests/` only when the private logic warrants them.

Sibling adapters still import only the sibling's top-level `run`; `contract.py` is not another exported API. The `run` annotations expose the boundary to static tooling, while each adapter translates into its owning brick's types.

Split a brick when `run` becomes a large dispatcher, its adapters stop being easy to understand, or unrelated changes repeatedly touch the same `src/`.

## Lanes

A lane is the enforcement class a brick declares for itself with `LANE` in `contract.py`. Every rule above applies to every brick; a lane only adds rules, so no brick can opt out of the boundary. A brick that declares no `LANE` is `strict`.

| Lane | What it means | What the linter adds |
| --- | --- | --- |
| `strict` | The regular brick. | Nothing beyond the rules every brick gets. |
| `pure` | Output is a function of input alone. | No adapters and no sibling dependencies. The direct-I/O ban that `src/` already carries widens to the whole brick, plus `random` and `time`, plus any `.now()`, `.today()`, or `.utcnow()` call. `runner/` is exempt because it records runs and owns `rng.py`; `datetime` stays importable for annotations and arithmetic. |
| `workflow` | Invoked as a whole operation, never imported for its parts. | No contract may name it as a sibling dependency. It alone may carry a process door, `__main__.py`, and that door may import nothing from the brick tree except the brick's own `run`. Smoke tests belong only here. |

A lane cannot exist without an enforcer: the `LANES` table in `tools/lint_bricks.py` maps each name to the function that checks it, and the linter rejects any other value.

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

`bricks/__init__.py` enables repository-wide standard-library test discovery. Each brick's top-level file defines its repository-internal entry point. Keep `runner/__init__.py`; add `runner/tests/__init__.py` only when that workflow has smoke tests. `input/`, `adapters/`, and `src/` do not need package-marker files.

Once at least one workflow has a smoke test, run all smoke tests with:

```sh
python3 -m unittest discover -s bricks -t . -v
```

Python's test runner exits with status 5 when no tests exist, which is the expected state of this empty boilerplate.

Check brick shape, import direction, public exports, and evidence limits with:

```sh
python3 tools/lint_bricks.py
```

The tools have their own tests:

```sh
python3 -m unittest discover -s tools/tests -t . -v
```

## The review gate

The linter decides everything an integer can decide. The rest of a lane is judgment, and `review/` holds it: `common.md` is the preamble every lane shares (what the linter already checked, what the model can and cannot see, how severity is assigned) and `<lane>.md` carries that lane's criteria. A change routed to a lane is judged by a model against those two files and returns findings, each `block` or `advisory`; a lane blocks only on a `block` finding.

The gate is for repositories built on this framework, not for the framework itself. `.github/workflows/review.yml` is a reusable workflow; a repository enables it with one file:

```yaml
# .github/workflows/review.yml
on: pull_request
jobs:
  review:
    uses: jtlacci/brick-framework/.github/workflows/review.yml@main
    secrets: inherit
```

Routing is derived from that repository's tree: a file under `bricks/<name>/` belongs to the lane its `contract.py` declares with `LANE` (`strict` when absent), and a file anywhere else is printed as not reviewed. The model reads the repository's `AGENTS.md`, `bricks/AGENTS.md`, the touched bricks' contracts and the diff, not the source tree, so the prompts forbid it from raising a finding whose only support is something it cannot see.

A repository adds a lane by adding `review/<lane>.md` of its own; a file there with a framework lane's name replaces the framework's prompt for that lane. The `pure` and `workflow` prompts describe the mechanical half as enforced by the linter; until the linter carries those lanes, no brick declares them and every brick is reviewed as `strict`.

Without an `ANTHROPIC_API_KEY` secret the job skips with a visible notice and passes; adding the secret turns the gate on. With the secret set, the review's exit status has three values: `0` passed, `1` blocked, `2` not reviewed (a provider failure that survived retries, a refusal, a misconfigured workflow). Not reviewed is a failure, not a pass. Verdicts are kept per pull request as a workflow artifact, so on the next push the model sees its own previous round and does not block the implementation of a suggestion it made; a push that touches no brick carries the previous verdict forward without a model call.

Run the same review locally from the reviewed repository's root, with `ANTHROPIC_API_KEY` exported and `pip install anthropic`:

```sh
python3 path/to/brick-framework/tools/review.py


The linter has its own tests, one per rule it enforces:

```sh
python3 -m unittest tools.tests.test_lint_bricks -v
```
