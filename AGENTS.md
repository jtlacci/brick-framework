# Repository contract

This repository uses Python file boilerplate to organize one codebase as discrete domain modules.

## Terminology

- The **repository boundary** separates this repository from APIs, databases, files, services, and other outside systems. Only these are called external.
- A **module boundary** separates one module from its sibling modules inside this repository.
- A **module entry point** is `run`. It is repository-internal and is called by sibling-module adapters.
- A **sibling adapter** is an adapter whose target is another module's `run` entry point.

## Purpose

- Optimize for human and agent visibility, not framework machinery.
- A module may be complex inside `src/`, but its inputs and recent runs must make its behavior understandable.
- Keep this repository as boilerplate. Do not add shared runtimes, generators, enforcement systems, or dependencies unless the user explicitly requests them.

## Non-negotiable rules

- Put every domain module in its own named folder under `modules/`.
- Every module has `input/`, `runner/`, and `src/`.
- A module exposes only its `run` entry point to sibling modules.
- External access crosses an external-source adapter; sibling-module access crosses a sibling adapter.
- Modules are used only inside this repository. Do not package or expose them for outside consumers.
- Saved adapter results and run records are local, bounded by configuration, and tracked in Git.
- Keep only a small number of high-level smoke tests.

## Contract precedence

This file applies to the whole repository. A nested `AGENTS.md` adds rules for its folder and descendants; it may not relax a parent rule.
