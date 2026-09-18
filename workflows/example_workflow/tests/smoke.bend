# Compiled whole-use-case smoke program through the example workflow boundary.
import Base
import ../contract.bend as Contract
import ../main.bend as Workflow

def assert_value(value: U32, is_expected: Bool) -> IO(Unit):
  match is_expected:
    case True{}:
      IO.print(U32.show(value))
    case False{}:
      IO.die(Unit, 1, "expected workflow output 42")

def assert_output(output: Contract.WorkflowOutput) -> IO(Unit):
  Contract.WorkflowOutput{+value} = output
  assert_value(value, U32.is_eq(value, 42))

def main() -> IO(Unit):
  do IO<Unit>:
    output : Contract.WorkflowOutput <- Workflow.run(Contract.WorkflowInput{21})
    assert_output(output)
