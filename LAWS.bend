# Human-owned laws for behavior that must survive every implementation change.
import Base
import ./bricks/example_brick/contract.bend as Contract
import ./bricks/example_brick/src/logic.bend as Logic

# LAW: the example transformation preserves its input value.
law example_preserves_value:
  for value: U32
  for run_id: Nat
  {Logic.execute(Contract.BrickInput{value}, Contract.RunContext{run_id})
    == Contract.BrickOutput{value} : Contract.BrickOutput}
