# Human-owned behavior that this brick must preserve.
import Base
import ./contract.bend as Contract
import ./src/logic.bend as Logic

# LAW: the example transformation preserves its input value.
law preserves_value:
  for value: U32
  for run_id: Nat
  {Logic.execute(Contract.BrickInput{value}, Contract.RunContext{run_id})
    == Contract.BrickOutput{value} : Contract.BrickOutput}
