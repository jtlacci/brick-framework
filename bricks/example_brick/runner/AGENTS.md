# Runner contract

This folder owns orchestration, brick-local run identity, run history, and smoke tests.

## Brick entry point

- `run.py` contains the brick's only repository-internal entry point: `run`.
- Annotate `run` with the brick's `BrickInput` and `BrickOutput` types from `contract.py`.
- `run` accepts ordinary inputs plus keyword-only `fresh` and `save` options. `save=True` implies a fresh call.
- `run` creates a run ID through `rng.py`, resolves configuration, builds a plain run context, calls `src/`, records the run outcome, and returns the result.
- `run` passes its caller-supplied brick input unchanged into `src` with the run context.
- `runner/` does not call input adapters directly and does not collect adapter-result references. Adapter calls and evidence belong to `src/` and `input/`.
- Run identity and mode are brick-local. They are not forwarded when an adapter invokes a sibling brick.
- Do not expose adapters or `src/` functions to sibling bricks.

## Run records

- Record every run, including failures and tests, under `runs/` using its brick-local run ID.
- Each run-outcome record includes the run ID, kind (`run` or `test`), mode (`saved`, `fresh`, or `save`), input, output or error, and timestamp.
- Input evidence captured by an explicit save operation carries the same run ID and can be joined outside the runner.
- Retain only the configured number of recent runs. Prune after recording the new run.
- Enforce `max_run_record_bytes` before writing a run record.
- Run records are intentionally tracked in Git. The human or agent operating the repository commits the resulting bounded history changes.

## Tests

- Smoke tests prove integration through the public brick boundary. Focused `src` tests prove domain correctness.
- `runner/tests/` is optional and reserved for the repository's most top-level flows: bricks that no other brick depends on.
- Do not add smoke tests to every brick. A top-level flow may have at most three smoke-test files, each defining an explicit input and calling only the brick's top-level `run`.
- Default tests use saved examples. A fresh test affects only its own brick; it never makes sibling runs fresh.
- Use a save test only when deliberately replacing reviewed committed examples.
- Focused tests under `src/tests/` are optional and may directly test private domain logic. Organize them only when the logic warrants it.
- If `runner/tests/` exists, keep its `__init__.py` so sibling bricks retain distinct test import paths during discovery.
