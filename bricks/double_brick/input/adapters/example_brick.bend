# Typed sibling boundary: this is the only place the double brick may call it.
import Base
import ../../contract.bend as Contract
import ../../../example_brick/contract.bend as ExampleContract
import ../../../example_brick/main.bend as Example

def output_value(output: ExampleContract.BrickOutput) -> U32:
  ExampleContract.BrickOutput{value} = output
  value

def call(value: U32) -> IO(U32):
  do IO<U32>:
    output : ExampleContract.BrickOutput <- Example.run(ExampleContract.BrickInput{value})
    return output_value(output)

def run(input: Contract.BrickInput) -> IO(U32):
  Contract.BrickInput{value} = input
  call(value)
