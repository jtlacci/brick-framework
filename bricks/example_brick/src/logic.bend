# Private domain logic. External effects belong behind input adapters.
import Base
import ../contract.bend as Contract

def execute(input: Contract.BrickInput, context: Contract.RunContext)
  -> Contract.BrickOutput:
  Contract.BrickInput{value} = input
  Contract.BrickOutput{value}
