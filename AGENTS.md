# Repository contract

This repository is boilerplate for domain bricks and application workflows.
Python is the example host language.

## Boundaries

- Put domain capabilities under `bricks/` and whole-use-case composition under `workflows/`.
- Each package exposes one typed `run(input) -> output` entry point.
- Bricks own domain behavior, state, and external adapters.
- Workflows translate values and sequence declared brick entries. They own no state or external effects and do not call other workflows.
- Cross-package access uses public entries and contracts only. Private source and runner modules are never imported across boundaries.

## Enforcement

- `tools/model_repository.py` is the mandatory structural linter. It reads source without importing application code and enforces package shape, contracts, dependency direction, import surfaces, effect placement, cycles, and state ownership.
- The host-language type checker validates actual brick and workflow connections. Python callers use the pinned strict mypy gate; another host language supplies its equivalent.
- Business behavior and examples belong in ordinary host-language tests. Architectural intent that syntax cannot prove belongs in semantic review; the existing optional gate covers brick lanes, while top-level workflows still require human review.
- A normal feature should not change framework enforcement code.

Keep the linter mechanical and standard-library-only. Use distinct semantic field types and explicit caller-owned translations at package boundaries.
