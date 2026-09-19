# Domain brick contract

Each direct child of `bricks/` owns one domain capability.

```text
<brick>/
├── __init__.py
├── contract.py
├── input/{adapters,data,config.yml}
├── runner/run.py
└── src/
```

- `contract.py` declares `BrickInput`, `BrickOutput`, `CONTRACT_VERSION`, `LANE`, `SIBLING_DEPENDENCIES`, and `OWNED_STATE` as literals.
- `__init__.py` exposes only `run` from `runner/run.py`.
- `run` accepts one `BrickInput` and returns one `BrickOutput`.
- `src/` owns private domain logic and reaches effects only through `input/adapters/`.
- A sibling adapter imports only the declared sibling's public `run`.
- `strict` is the regular lane. `pure` declares no dependencies or external adapters.
- Bricks never import workflows.

Use normal host-language tests for behavior.
