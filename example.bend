# End-to-end composition through the public workflow boundary.
import Base
import ./workflows/example_workflow/contract.bend as Contract
import ./workflows/example_workflow/main.bend as Workflow

def print_output(output: Contract.WorkflowOutput) -> IO(Unit):
  Contract.WorkflowOutput{value} = output
  IO.print(U32.show(value))

def main() -> IO(Unit):
  do IO<Unit>:
    output : Contract.WorkflowOutput <- Workflow.run(Contract.WorkflowInput{21})
    print_output(output)
