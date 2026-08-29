# Repository contract

This repository is Python file boilerplate for codebases built as discrete domain modules.

## Purpose

- Optimize for human and agent visibility, not framework machinery.
- A module may be complex inside `src/`, but its inputs and recent runs must make its behavior understandable.
- Keep this repository as boilerplate. Do not add shared runtimes, generators, enforcement systems, or dependencies unless the user explicitly requests them.

## Non-negotiable rules

- Put every domain module in its own named folder under `modules/`.
- Every module has `input/`, `runner/`, and `src/`.
- A module exposes only its `run` function publicly.
- All external access, including access to another module, crosses an adapter boundary.
- Saved adapter results and run records are local, bounded by configuration, and tracked in Git.
- Keep only a small number of high-level smoke tests.

## Contract precedence

This file applies to the whole repository. A nested `AGENTS.md` adds rules for its folder and descendants; it may not relax a parent rule.
