# Repository contract

This repository uses Python file boilerplate to organize one codebase as discrete domain bricks.

## Terminology

- The **repository boundary** separates this repository from APIs, databases, files, services, and other outside systems. Only these are called external.
- A **brick boundary** separates one brick from its sibling bricks inside this repository.
- A **brick entry point** is `run`. It is repository-internal and is called by sibling-brick adapters.
- A **sibling adapter** is an adapter whose target is another brick's `run` entry point.

## Purpose

- Optimize for human and agent visibility, not framework machinery.
- A brick may be complex inside `src/`, but its inputs and recent runs must make its behavior understandable.
- Keep this repository as boilerplate. Do not add shared runtimes, generators, dependencies, or heavier enforcement unless the user explicitly requests them.
- Keep enforcement in `tools/lint_bricks.py` lightweight and standard-library-only.

## Non-negotiable rules

- Put every domain brick in its own named folder under `bricks/`.
- Every brick has `input/`, `runner/`, and `src/`.
- Every brick declares a typed, versioned input and output boundary in `contract.py`.
- A brick exposes only its `run` entry point to sibling bricks.
- External access crosses an external-source adapter; sibling-brick access crosses a sibling adapter.
- Every sibling dependency declares its consistency policy as `eventual` or `orchestrated`. Dependency cycles are not allowed; introduce or reshape a parent brick instead.
- Every persistent application-state resource has exactly one owning brick. Brick-local evidence folders are owned implicitly by their brick.
- Bricks are used only inside this repository. Do not package or expose them for outside consumers.
- Saved adapter examples and run records are local, bounded by configuration, and tracked in Git.
- Keep only a small number of high-level smoke tests, while allowing focused tests for complex `src/` logic.

## Contract placement and precedence

`AGENTS.md` rules apply to their folder and descendants. A nested `AGENTS.md` adds rules for its subtree and may not relax a parent rule.

Not every folder needs an `AGENTS.md`. Add one only where the folder introduces a distinct responsibility or additional rule. This boilerplate keeps contracts at the repository root, `bricks/`, and each brick's `input/`, `runner/`, and `src/` boundaries. A brick-level `AGENTS.md` is optional and should contain only domain-specific additions.

## When to split a brick

Split or reshape a brick when its `run` becomes a large operation dispatcher, its adapter set is no longer easy to understand, or unrelated changes repeatedly touch the same `src/`. Encapsulation is not permission for an internal monolith.
