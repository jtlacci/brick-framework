# Source contract

This folder owns the brick's private domain logic. Its internal organization is otherwise unrestricted.

- Do not perform network, database, filesystem, subprocess, environment, clock, or other external I/O here.
- Do not import adapters or other bricks here.
- Receive configuration and external data as ordinary function arguments from `runner/`.
- Libraries are allowed only when their use is local and does not make external calls.
- Keep behavior deterministic for the same supplied inputs unless randomness is explicitly passed in.
- Export functions only for use by this brick's `runner/`; the repository-internal brick entry point remains `run` alone.
