# The workflow lane

Everything in the strict lane applies. A workflow is invoked as a whole
operation and never depended on; the linter has already confined
`__main__.py` to this lane. You judge whether the brick is
still a composition and not a domain in disguise.

## What to judge

Criteria 1–8 of the strict lane, then:

9. **The runner composes; it does not compute.** `runner/run.py` and
   `__main__.py` create the run context, call `src/`, and record the outcome.
   A diff that puts a decision, a calculation, a retry policy or a data
   transformation into either — anything an evaluation would want to reach —
   has moved domain logic to the one place the lane's rules do not follow it.
   Block.

10. **Orchestration is real.** A workflow is where `orchestrated` sibling
    dependencies are honoured: it sequences the sibling calls and compensates
    when a later one fails. A diff that adds an `orchestrated` dependency and
    no sequencing, or that leaves a partial failure with no compensation and no
    stated reason, blocks.

11. **The door does no io of its own.** `__main__.py` starts the loop and calls
    `run`. Anything it reads from outside — a feed, a file, an environment value
    that changes behaviour — must come through an adapter, or evaluation cannot
    replay it. Block.

## Severity

Criteria **9, 10 and 11 block**. The strict lane's severities stand for
criteria 1–8.
