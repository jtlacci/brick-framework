# End-to-end composition through two public brick boundaries.
import Base
import ./bricks/double_brick/contract.bend as Contract
import ./bricks/double_brick/main.bend as Double

def print_output(output: Contract.BrickOutput) -> IO(Unit):
  Contract.BrickOutput{value} = output
  IO.print(U32.show(value))

def main() -> IO(Unit):
  do IO<Unit>:
    output : Contract.BrickOutput <- Double.run(Contract.BrickInput{21})
    print_output(output)
