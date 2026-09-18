# Runner contract

This folder owns brick-local execution context and the handoff to private logic.

- `run.bend` defines `run(input: Contract.BrickInput) -> IO(Contract.BrickOutput)`.
- Build brick-local context here and pass the caller's input plus that context into `src/` unchanged.
- Runner-owned effects such as clock access may be sequenced here. Adapter effects are requested by `src/` and implemented in `input/adapters/`.
- Do not import sibling bricks, input adapters, or another brick's internals.
- A `Workflow{}` brick may have at most three executable Bend smoke programs under `runner/tests/`. Each imports only the brick's `main.bend` and exercises `run` as a whole.
