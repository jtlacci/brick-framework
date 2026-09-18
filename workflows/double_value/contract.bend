# Typed public boundary and literal brick dependencies for this workflow.
import Base

type BrickDependency is Data:
  BrickDependency{name: String}

type WorkflowInput is Data:
  WorkflowInput{value: U32}

type WorkflowOutput is Data:
  WorkflowOutput{value: U32}

# Keep these definitions literal: repository tools inspect them without
# executing project code.
def contract_version() -> U32:
  1

def brick_dependencies() -> List<&2, BrickDependency>:
  [BrickDependency{"example_brick"}]
