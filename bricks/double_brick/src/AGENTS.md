# Source contract

This folder owns private domain logic.

- Receive typed brick input and explicit context from `runner/`.
- Keep pure transformations separate from effects so `laws.bend` can state useful invariants over them.
- Route files, clocks, environment, networking, graphics, audio, randomness, and sibling calls through this brick's input adapters.
- Do not import `runner/` or any sibling brick directly.
- Use parallel calls only when the calls are independent and balanced.
- Do not use `@unsafe` to evade termination checking or a failed proof.
- Export definitions only for this brick's runner, adapters, laws, and proofs; the repository-internal entry point remains `main.bend`'s `run`.
