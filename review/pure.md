# The pure lane

Everything in the strict lane applies, and the linter has already removed
adapters, sibling dependencies, direct I/O, `random`, `time` and clock calls
from this brick. What remains is the claim the lane makes and a parser cannot
verify: **the output is a function of the input alone.**

## What to judge

Criteria 1–8 of the strict lane, then:

9. **Hidden inputs.** Anything `src/` reads that did not arrive in the brick
   input is a second input the contract does not declare: a module-level
   mutable, a class attribute mutated across calls, a field of the run context
   other than the input, a config value read inside `src/`, a default argument
   evaluated once. A diff that introduces one blocks.

10. **Semantic nondeterminism.** Iteration over a set or over dict keys derived
    from hashed objects, float accumulation whose order the output depends on,
    `id()`-based ordering, thread timing. If two calls with the same input can
    return different outputs, the brick is not pure. Block when the output
    depends on it; advisory when only an internal order does.

11. **Purity by relocation.** A diff that keeps `src/` pure by moving the
    effect into `runner/` — a runner that reads a file, calls a service, or
    seeds the input from the environment before calling `src/` — has hidden the
    effect where the lane does not look. The runner records runs and owns the
    RNG; it is not a second `input/`. Block.

## Severity

Criteria **9 and 11 block**; criterion 10 blocks when the output depends on
it. The strict lane's severities stand for criteria 1–8.
