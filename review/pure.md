# The pure lane

Everything in the strict lane applies. The linter has already removed adapters, sibling dependencies, foreign imports, and Base effects. What remains is the semantic claim: **the output is a function of the typed input alone.**

## What to judge

Criteria 1–8 of the strict lane, then:

9. **No hidden inputs.** A configuration constant, run context field, captured value, compile-time package value, or mutable foreign state that changes the result without appearing in `BrickInput` is a second input. Block.

10. **No semantic nondeterminism.** Parallel evaluation may change scheduling but not results. Order-sensitive floating-point aggregation, data races hidden in a foreign, or another construction that can yield different outputs for the same input violates the lane. Block when output depends on it; advisory when only internal work order changes.

11. **No purity by relocation.** Wrapping a file, clock, environment, network, or random read in `runner/` and then passing its result into pure `src/` does not make the brick pure. The runner may only lift the input-derived result with `IO.pure`. Block.

## Severity

Criteria **9 and 11 block**; criterion 10 blocks when output depends on it. The strict lane severities stand for criteria 1–8.
