# Workflow contract

Each direct child of `workflows/` is one application use case. A workflow composes bricks; it does not own domain logic, state, or infrastructure.

- Keep one typed `WorkflowInput`, one typed `WorkflowOutput`, and one public `run(input) -> IO(output)` entry point.
- Declare brick dependencies by name in `contract.bend`. The declared set must exactly match the bricks imported by `flow.bend`.
- Call a brick only through its `contract.bend` datatypes and `main.bend` `run` entry point.
- Put pure request translation, result translation, and sequencing in `flow.bend`.
- Perform no direct external effects. Files, clocks, databases, APIs, environment access, foreign code, and other capabilities belong behind brick boundaries.
- Do not import another workflow. This is a v1 restriction; reusable orchestration should become a brick with a domain-owned contract.
- State pure translation and planning invariants in `laws.bend` and prove them in `proof.bend`.
- Keep one to three compiled programs under `tests/`. They import only the workflow's public contract and entry point and exercise a whole use case.
