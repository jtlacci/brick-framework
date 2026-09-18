# The only executable module sibling bricks may import.
import Base
import ./contract.bend as Contract
import ./runner/run.bend as Runner

def run(input: Contract.BrickInput) -> IO(Contract.BrickOutput):
  Runner.run(input)
