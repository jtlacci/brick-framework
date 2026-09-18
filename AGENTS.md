# Repository contract

This repository uses Bend 2 file boilerplate to organize one codebase as discrete domain bricks. Python is host-side repository tooling only; brick behavior belongs in `.bend` files.

## Before editing Bend

- Run `bend guide` and use the installed compiler as the syntax authority.
- Read the closest inherited `AGENTS.md` files.
- Keep each brick's human intent in its `laws.bend` and its implementations in `proof.bend`; keep root `LAWS.bend` and `PROOF.bend` complete as aggregators.
- Run `bend PROOF.bend` after every behavior change and before committing.
- Use Bend parallel calls only for independent, balanced work.

## Terminology

- The **repository boundary** separates this repository from APIs, databases, files, services, and other outside systems.
- A **brick boundary** separates one brick from its sibling bricks.
- A **brick entry point** is `run` in the brick's `main.bend`.
- A **sibling adapter** imports another brick's `contract.bend` for boundary types and `main.bend` for execution, then calls only `run`.

## Non-negotiable rules

- Put every domain brick in its own named folder under `bricks/`.
- Every brick has `input/`, `runner/`, and `src/` boundaries plus `main.bend` and `contract.bend`.
- Every brick declares typed `BrickInput` and `BrickOutput` datatypes and literal version, lane, dependency, and state-ownership metadata in `contract.bend`.
- A brick exposes contract datatypes plus the single executable entry point `run`, which returns `IO(BrickOutput)`.
- External access crosses an input adapter; sibling access crosses a sibling adapter.
- Every sibling dependency declares `Eventual{}` or `Orchestrated{}` consistency. Dependency cycles are forbidden.
- Every persistent application-state resource has exactly one owning brick.
- Bricks are repository-internal. Do not package or expose them to outside consumers.
- State important invariants as brick-owned Bend laws and keep the root proof aggregation complete.
- Keep enforcement in `tools/lint_bricks.py` lightweight and standard-library-only.

## Contract placement and precedence

`AGENTS.md` rules apply to their folder and descendants. A nested file may add rules but never relax a parent rule. Add a brick-level contract only for domain-specific additions.

## When to split a brick

Split or reshape a brick when `run` becomes a large operation dispatcher, its adapter set is no longer easy to understand, or unrelated changes repeatedly touch the same `src/` code.
