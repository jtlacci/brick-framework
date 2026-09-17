# The workflow lane

Everything in the strict lane applies. A workflow is invoked as a whole
operation and never depended on; the linter has already confined
`__main__.py` and the smoke tests to this lane. You judge whether the brick is
still a composition and not a domain in disguise.

## What to judge

Criteria 1–8 of the strict lane, then:

9. **The runner composes; it does not compute.** `runner/run.py` and
   `__main__.py` create the run context, call `src/`, and record the outcome.
   A diff that puts a decision, a calculation, a retry policy or a data
   transformation into either — anything a focused test would want to reach —
   has moved domain logic to the one place the lane's rules do not follow it.
   Block.

10. **Orchestration is real.** A workflow is where `orchestrated` sibling
    dependencies are honoured: it sequences the sibling calls and compensates
    when a later one fails. A diff that adds an `orchestrated` dependency and
    no sequencing, or that leaves a partial failure with no compensation and no
    stated reason, blocks.

11. **Smoke tests go through the door.** A smoke test defines one explicit
    input, calls the brick's top-level `run`, and asserts on the output. A
    smoke test that imports `src/`, patches an adapter, or reaches into a
    sibling is a focused test in the wrong folder. Advisory — unless it makes
    a sibling run fresh, which the boundary forbids and which blocks.

## Severity

Criteria **9 and 10 block**; criterion 11 blocks only when it makes a sibling
run fresh. The strict lane's severities stand for criteria 1–8.
