# Placeholder brick contract

This folder demonstrates the required shape of one repository-internal domain brick. It is not a distributable package.

- Replace the placeholder name and stubs when defining a real domain here.
- Keep the `input/`, `runner/`, and `src/` contracts in every brick in this repository.
- Keep the top-level `__init__.py` limited to exposing the internal `run` entry point.
- Sibling bricks may use this brick only through an adapter that calls `run`.
