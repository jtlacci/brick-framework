# End-to-end composition through the public workflow boundary.
import Base
import ./workflows/double_value/contract.bend as Contract
import ./workflows/double_value/main.bend as Workflow

def print_output(output: Contract.WorkflowOutput) -> IO(Unit):
  Contract.WorkflowOutput{value} = output
  IO.print(U32.show(value))

def main() -> IO(Unit):
  do IO<Unit>:
    output : Contract.WorkflowOutput <- Workflow.run(Contract.WorkflowInput{21})
    print_output(output)
