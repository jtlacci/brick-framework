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
- `review/<lane>.md` contains stable semantic criteria that syntax cannot prove. `tools/review.py` sends those bounded criteria to Jev and treats Jev's blocking classifications as merge failures.
- Business behavior and examples belong in ordinary host-language tests. A normal feature should not change framework enforcement code or policy criteria.

Keep the linter mechanical and standard-library-only. Keep semantic policy criteria explicit, independently answerable, and identified by stable IDs.
