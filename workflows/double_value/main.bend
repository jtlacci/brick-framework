# The workflow's only executable entry point.
import Base
import ./contract.bend as Contract
import ./flow.bend as Flow

def run(input: Contract.WorkflowInput) -> IO(Contract.WorkflowOutput):
  Flow.run(input)
