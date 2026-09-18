# Human-owned behavior that this brick must preserve.
import Base
import ./contract.bend as Contract
import ./src/logic.bend as Logic

# LAW: the brick doubles the value returned through its dependency boundary.
law doubles_dependency_value:
  for value: U32
  {Logic.finish(value)
    == Contract.BrickOutput{(value + value : U32)} : Contract.BrickOutput}
