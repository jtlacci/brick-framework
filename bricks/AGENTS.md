# Domain brick contract

Each direct child of `bricks/` is one domain brick. Parent repository rules apply.

## Required shape

```text
<brick_name>/
├── main.bend
├── contract.bend
├── laws.bend
├── proof.bend
├── input/
│   ├── AGENTS.md
│   ├── config.bend
│   └── adapters/
├── runner/
│   ├── AGENTS.md
│   └── run.bend
└── src/
    └── AGENTS.md
```

## Boundaries

- `main.bend` is the sole sibling-call surface. It imports `contract.bend` and `runner/run.bend`, defines only `run`, and returns `IO(BrickOutput)`.
- `contract.bend` declares `BrickInput`, `BrickOutput`, `Lane` (`Strict{}` or `Pure{}`), `Consistency`, `Dependency`, and literal `contract_version`, `lane`, `sibling_dependencies`, and `owned_state` definitions.
- `input/` owns typed configuration plus every external-source and sibling adapter.
- `runner/` creates brick-local context and hands execution to private logic. Runner-owned effects such as clock access stay here; adapter effects are requested by `src/`.
- `src/` owns private domain logic and may call only its own adapters for effects.
- Adapters never import `src/` or `runner/`.
- A sibling adapter may import the sibling's `contract.bend` for boundary datatypes and `main.bend` for `run`. Do not import another brick's source, runner, configuration, or data.
- Sibling run identity and effect policy stay local to the called brick.
- Foreign C or JavaScript implements effects only. Keep validation, translation, branching, and domain decisions in Bend.
- Parallel calls must be independent and balanced. Do not add `@unsafe` merely to bypass termination or proof failures.

## Laws

Add non-negotiable behavior to the brick's `laws.bend` and fill it in that brick's `proof.bend`. The root `LAWS.bend` and `PROOF.bend` aggregate every brick and workflow so one command checks the repository. Prefer laws over pure functions at the `src/` or adapter-normalization boundary. Never weaken a law to accommodate an implementation.
