# Private domain logic. Sibling effects cross this brick's local adapter.
import Base
import ../contract.bend as Contract
import ../input/adapters/example_brick.bend as ExampleAdapter

def finish(+value: U32) -> Contract.BrickOutput:
  Contract.BrickOutput{(value + value : U32)}

def execute(input: Contract.BrickInput, context: Contract.RunContext)
  -> IO(Contract.BrickOutput):
  do IO<Contract.BrickOutput>:
    value : U32 <- ExampleAdapter.run(input)
    return finish(value)
