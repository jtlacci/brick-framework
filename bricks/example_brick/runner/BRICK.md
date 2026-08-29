# Runner contract

This folder owns orchestration, run identity, run history, and smoke tests.

## Brick entry point

- `run.py` contains the brick's only repository-internal entry point: `run`.
- `run` creates a run ID through `rng.py`, resolves configuration, builds a plain run context, calls `src/`, records the run outcome, and returns the result.
- `run` passes its caller-supplied brick input unchanged into `src` with the run context.
- `runner/` does not call input adapters directly. Adapter calls belong to `src/`.
- Do not expose adapters or `src/` functions to sibling bricks.

## Run records

- Record every run, including failures and tests, under `runs/` using its run ID.
- Each run-outcome record includes the run ID, kind (`run` or `test`), mode (`saved` or `fresh`), input, adapter-result references, output or error, and timestamp.
- Retain only the configured number of recent runs. Prune after recording the new run.
- Run records are intentionally tracked in Git. The human or agent operating the repository commits the resulting history changes.

## Tests

- Keep only a handful of high-level smoke tests under `tests/`.
- Use one file per smoke test.
- Each smoke test defines an explicit input and passes it directly to `run`.
- Keep `runner/__init__.py` and `runner/tests/__init__.py` so sibling bricks with the same test filenames retain distinct import paths during discovery.
- Tests use saved adapter data by default. `--FRESH` performs real adapter calls and updates saved data.
- Do not add a large unit-test hierarchy unless the user explicitly requests it.
