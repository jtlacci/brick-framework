# Example workflow translations and sequencing through declared brick entry points.
import Base
import ./contract.bend as Contract
import ../../bricks/example_brick/contract.bend as ExampleContract
import ../../bricks/example_brick/main.bend as Example

def request(input: Contract.WorkflowInput) -> ExampleContract.BrickInput:
  Contract.WorkflowInput{value} = input
  ExampleContract.BrickInput{value}

def output_value(output: ExampleContract.BrickOutput) -> U32:
  ExampleContract.BrickOutput{value} = output
  value

def finish(+value: U32) -> Contract.WorkflowOutput:
  Contract.WorkflowOutput{(value + value : U32)}

def run(input: Contract.WorkflowInput) -> IO(Contract.WorkflowOutput):
  do IO<Contract.WorkflowOutput>:
    output : ExampleContract.BrickOutput <- Example.run(request(input))
    return finish(output_value(output))
