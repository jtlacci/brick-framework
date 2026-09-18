# Workflow contract

Each direct child of `workflows/` is one whole application use case.

- `contract.py` declares one `WorkflowInput`, one `WorkflowOutput`, a positive `CONTRACT_VERSION`, and literal `BRICK_DEPENDENCIES`.
- `__init__.py` exposes only `run` from `flow.py`.
- `flow.py` translates values and sequences only declared brick public entries and contracts.
- Workflows do not own state, access infrastructure directly, or import another workflow.
- Workflow behavior is tested in the host language. No workflow-local Bend laws or runtime files are allowed.

The framework's stable Bend law validates workflow structure from the generated repository model.
