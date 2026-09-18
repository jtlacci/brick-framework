# The workflow profile

A workflow is an application use case invoked as a whole. The linter has already checked its single typed entry, declared brick dependencies, import boundary, direct-effect ban, laws, proofs, and smoke-program shape. You judge whether it remains composition rather than becoming a domain brick in disguise.

## What to judge

Apply the semantic parts of criteria 1–8 from the strict profile, then:

9. **Composition only.** `flow.bend` sequences declared brick `run` calls and translates their typed values; it does not accumulate domain rules that belong in a brick.

10. **Whole-operation contract.** `WorkflowInput` and `WorkflowOutput` describe one coherent use case, not a generic command dispatcher.

11. **Capability isolation.** Infrastructure and external behavior remain owned by bricks. The workflow does not disguise an effect in a helper.

12. **Smoke value.** Each smoke program exercises the public `run` boundary and a meaningful whole-use-case outcome. It does not merely compile or print a constant.

## Severity

Criteria **9–11 block**. Criterion 12 is advisory unless it exposes a blocking defect. The strict-profile severities stand for criteria 1–8.
