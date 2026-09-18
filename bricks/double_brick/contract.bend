# Typed boundary and machine-readable ownership declarations for this brick.
import Base

type Lane is Data:
  Strict{}
  Pure{}
  Workflow{}

type Consistency is Data:
  Eventual{}
  Orchestrated{}

type Dependency is Data:
  Dependency{name: String, consistency: Consistency}

type BrickInput is Data:
  BrickInput{value: U32}

type BrickOutput is Data:
  BrickOutput{value: U32}

type RunContext is Data:
  RunContext{run_id: Nat}

# Keep these four definitions literal: the repository tools inspect them
# without executing project code.
def contract_version() -> U32:
  1

def lane() -> Lane:
  Strict{}

def sibling_dependencies() -> List<&2, Dependency>:
  [Dependency{"example_brick", Orchestrated{}}]

def owned_state() -> List<&2, String>:
  []
