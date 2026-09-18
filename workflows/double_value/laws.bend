# Human-owned invariants for pure workflow translation and result shaping.
import Base
import ./contract.bend as Contract
import ./flow.bend as Flow
import ../../bricks/example_brick/contract.bend as ExampleContract

# LAW: translating a workflow request preserves its value.
law request_preserves_value:
  for value: U32
  {Flow.request(Contract.WorkflowInput{value})
    == ExampleContract.BrickInput{value} : ExampleContract.BrickInput}

# LAW: the workflow doubles the value returned by its brick dependency.
law doubles_brick_value:
  for value: U32
  {Flow.finish(value)
    == Contract.WorkflowOutput{(value + value : U32)} : Contract.WorkflowOutput}
