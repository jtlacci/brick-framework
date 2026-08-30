# Input contract

This folder owns every external-source boundary and sibling-brick boundary for the brick.

## Configuration

- Keep brick configuration in `config.yml`.
- Keep run, saved-example, and byte limits in that file.
- Never store credentials or secrets in committed configuration or saved evidence.

## Adapters

- Create one Python file under `adapters/` for each external source or sibling brick.
- APIs, databases, filesystems, queues, clocks, and services are external sources beyond the repository boundary.
- Other bricks in this repository are sibling bricks, not external sources.
- An adapter fetches or sends data; it does not contain domain logic.
- A sibling adapter calls only the sibling brick's `run` entry point.
- Adapters are called by `src/` with a plain run context containing the owning brick's run ID, mode, and resolved adapter configuration.
- Adapters never import or call `src/` or `runner/`.
- A sibling adapter never forwards `fresh`, `save`, the parent run ID, or other run-control state. The sibling run remains fully contained and creates its own identity.

## Git-stable saved examples

- Store committed examples at `data/<adapter>/<case>.json`, using stable human-readable adapter and case names.
- Default saved mode reads the named example and fails clearly if it is absent or its normalized request does not match. It never falls through to a live call.
- `fresh=True` (the `--FRESH` run option) calls the real source and does not modify committed examples.
- `save=True` (the `--SAVE` run option) implies a fresh call, redacts sensitive fields, checks size limits, and atomically replaces the named committed example.
- A saved example contains `schema_version`, `contract_version`, `adapter`, `case`, `capture_run_id`, normalized `request`, and exactly one of `response` or `error`.
- Refuse to replay an example captured under a different brick contract version.
- Serialize JSON with sorted keys, two-space indentation, and a trailing newline. Do not store headers, credentials, cookies, tokens, or other secrets.
- Enforce `max_evidence_bytes` after serialization and before replacement. Keep no more than `saved_examples_per_adapter` cases for one adapter.
- The capture run and its saved adapter evidence can be correlated outside the execution loop through `capture_run_id`; the runner does not gather adapter references.
- Saved examples are intentionally tracked in Git. Only an explicit save operation should normally change them.
