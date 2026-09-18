# Compile-time configuration for the example brick.
import Base
import ../contract.bend as Contract

def run_context(run_id: Nat) -> Contract.RunContext:
  Contract.RunContext{run_id}
