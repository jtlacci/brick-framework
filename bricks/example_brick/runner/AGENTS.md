# Runner contract

This folder owns orchestration, brick-local run identity, run history, and smoke tests.

## Brick entry point

- `run.py` contains the brick's only repository-internal entry point: `run`.
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

- Keep only a handful of high-level smoke tests under `tests/`.
- Use one file per smoke test. Each smoke test defines an explicit input and passes it directly to `run`.
- Default tests use saved examples. A fresh test affects only its own brick; it never makes sibling runs fresh.
- Use a save test only when deliberately replacing reviewed committed examples.
- Focused unit tests inside `src/` are allowed when its domain logic needs them; avoid a large framework-driven test hierarchy.
- Keep `runner/__init__.py` and `runner/tests/__init__.py` so sibling bricks with the same test filenames retain distinct import paths during discovery.
