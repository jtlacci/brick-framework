# Brick-local context and handoff to private domain logic.
import Base
import ../contract.bend as Contract
import ../input/config.bend as Config
import ../src/logic.bend as Logic

def run(input: Contract.BrickInput) -> IO(Contract.BrickOutput):
  do IO<Contract.BrickOutput>:
    run_id : Nat <- IO.now()
    context : Contract.RunContext = Config.run_context(run_id)
    output : Contract.BrickOutput <- Logic.execute(input, context)
    return output
