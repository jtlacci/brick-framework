# Source contract

This folder owns the brick's private domain logic. Its internal organization is otherwise unrestricted.

- Receive the brick input and a plain run context from `runner/`.
- Decide when external or sibling-brick data is needed and call adapters from this brick's `input/` folder.
- Pass the run context into every adapter so it can apply saved, fresh, or save behavior.
- Do not implement mode branching here; each adapter owns that behavior using the mode in the run context.
- Do not perform direct network, database, filesystem, subprocess, environment, clock, or sibling-brick calls. Those calls must go through adapters.
- Do not import sibling bricks directly. Import only this brick's input adapters.
- Libraries are allowed only when their use is local and does not make external calls.
- Keep behavior deterministic for the same supplied inputs unless randomness is explicitly passed in.
- Export functions only for use by this brick's `runner/`; the repository-internal brick entry point remains `run` alone.
