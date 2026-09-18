# Stable framework law. Package behavior does not belong here.
import Base
import ./ARCHITECTURE.bend as Architecture
import ./verification/rules.bend as Rules

law repository_obeys_framework:
  {Rules.validate(Architecture.repository()) == True{} : Bool}
