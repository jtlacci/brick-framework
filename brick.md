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
- Keep this repository as boilerplate. Do not add shared runtimes, generators, enforcement systems, or dependencies unless the user explicitly requests them.

## Non-negotiable rules

- Put every domain brick in its own named folder under `bricks/`.
- Every brick has `input/`, `runner/`, and `src/`.
- A brick exposes only its `run` entry point to sibling bricks.
- External access crosses an external-source adapter; sibling-brick access crosses a sibling adapter.
- Bricks are used only inside this repository. Do not package or expose them for outside consumers.
- Saved adapter results and run records are local, bounded by configuration, and tracked in Git.
- Keep only a small number of high-level smoke tests.

## Contract precedence

This file applies to the whole repository. A nested `brick.md` adds rules for its folder and descendants; it may not relax a parent rule.
