# The workflow lane

Everything in the strict lane applies. A workflow is invoked as a whole and never depended on; the linter has confined `app.bend` and smoke programs to this lane. You judge whether the brick remains composition rather than becoming a domain in disguise.

## What to judge

Criteria 1–8 of the strict lane, then:

9. **The runner composes; it does not compute.** `runner/run.bend` and `app.bend` create context, sequence calls, and return or present the result. A domain decision, calculation, retry rule, or data transformation in either belongs in `src/` or an adapter-normalization function. Block.

10. **Orchestration is real.** A workflow is where `Orchestrated{}` dependencies are honored. Adding one without sequencing, or leaving a partial failure with neither compensation nor an explicit invariant explaining why compensation is unnecessary, blocks.

11. **Smoke programs use the public door.** A smoke program defines explicit input, imports only the brick's `main.bend`, executes `run`, and fails observably on a wrong result. Reaching into `src/`, patching an adapter, or importing a sibling makes it a focused check in the wrong folder. Advisory unless it also violates a blocking boundary.

## Severity

Criteria **9 and 10 block**. Criterion 11 is advisory unless it exposes a blocking strict-lane defect. The strict lane severities stand for criteria 1–8.
