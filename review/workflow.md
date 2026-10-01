# Workflow semantic policy

### workflow-1: The workflow contains composition only

Outcomes: pass, block

`flow.py` translates values and sequences declared brick `run` calls. Domain
rules belong in bricks; domain behavior in the workflow blocks.

### workflow-2: The contract describes one whole operation

Outcomes: pass, advisory, block

`WorkflowInput` and `WorkflowOutput` describe one coherent use case, not a
generic dispatcher. A dispatcher is advisory unless it hides a dependency or
boundary, which blocks.

### workflow-3: Capabilities remain isolated in bricks

Outcomes: pass, block

Infrastructure and external behavior remain owned by bricks. A disguised
workflow effect blocks.

### workflow-4: Meaningful orchestration has host-language evidence

Outcomes: pass, advisory

Meaningful sequencing, translation, and failure behavior should be covered by
ordinary host-language tests. Missing high-value coverage is advisory.
