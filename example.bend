# End-to-end use of the example brick through its public boundary.
import Base
import ./bricks/example_brick/contract.bend as Contract
import ./bricks/example_brick/main.bend as Example

def print_output(output: Contract.BrickOutput) -> IO(Unit):
  Contract.BrickOutput{value} = output
  IO.print(U32.show(value))

def main() -> IO(Unit):
  do IO<Unit>:
    output : Contract.BrickOutput <- Example.run(Contract.BrickInput{42})
    print_output(output)
