# Runner contract

This folder owns top-level orchestration and brick-local execution context.

- `run.bend` defines `run(input: Contract.BrickInput) -> IO(Contract.BrickOutput)`.
- Build brick-local context here and pass the caller's input plus that context into `src/` unchanged.
- Sequence the run's top-level effects here, but keep domain decisions in `src/` and effect implementations in `input/adapters/`.
- Do not import sibling bricks or another brick's internals.
- A `Workflow{}` brick may have at most three executable Bend smoke programs under `runner/tests/`. Each imports only the brick's `main.bend` and exercises `run` as a whole.
