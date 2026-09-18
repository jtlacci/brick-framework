# The workflow profile

A workflow is one host-language application use case. Bend has checked its structural boundary; you judge whether it remains composition.

## What to judge

1. **Composition only.** `flow.py` translates values and sequences declared brick `run` calls. Domain rules belong in bricks. Domain behavior in the workflow blocks.

2. **Whole-operation contract.** `WorkflowInput` and `WorkflowOutput` describe one coherent use case, not a generic dispatcher. A dispatcher is advisory unless it hides a dependency.

3. **Capability isolation.** Infrastructure and external behavior remain owned by bricks. A disguised workflow effect blocks.

4. **Host-language evidence.** Meaningful orchestration behavior is tested normally in the host language. Do not add workflow-local Bend laws or executable Bend examples.

## Severity

Criteria **1 and 3 block**. Criteria 2 and 4 are advisory unless they expose a blocking boundary defect.
