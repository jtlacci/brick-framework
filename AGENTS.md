# Repository contract

This repository is language-neutral boilerplate for domain bricks and application workflows. Python is the example host language. Bend is a CI-only structural verifier; application behavior never belongs in Bend.

## Boundaries

- Put domain capabilities under `bricks/` and whole-use-case composition under `workflows/`.
- Each package exposes one typed `run(input) -> output` entry point.
- Bricks own domain behavior, state, and external adapters.
- Workflows translate values and sequence declared brick entry points. They own no state or external effects and do not call other workflows.
- Cross-package access uses public entries and contracts only. Private source and runner modules are never imported across boundaries.

## Bend verification

- `tools/model_repository.py` is the host-language linter and trusted source frontend. It validates local shape and extracts filesystem, contract, import, and recognizable-effect facts without importing application code.
- `ARCHITECTURE.bend` is generated. Never edit it by hand.
- `verification/rules.bend` owns stable relational rules over those facts for dependencies, lanes, imports, cycles, and state ownership.
- `LAWS.bend` and `PROOF.bend` prove the generated repository model satisfies those rules.
- Package behavior, examples, semantic purity, and business invariants belong in host-language tests and review, not Bend laws.
- Regenerate after architecture changes with `python3 tools/model_repository.py --write`, then run `bend PROOF.bend`.

Keep the extractor mechanical and standard-library-only. A normal brick behavior change should not change any Bend law.
