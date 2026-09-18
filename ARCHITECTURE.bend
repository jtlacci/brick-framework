# Generated repository facts. Run: python3 tools/model_repository.py --write
import Base
import ./verification/rules.bend as Rules

# Package ids: 1=example_brick, 2=example_workflow
# State ids: none
def repository() -> Rules.Repository:
  Rules.Repository{
    [
      Rules.Package{1, Rules.Brick{}, Rules.Strict{}, 0, [], True{}},
      Rules.Package{2, Rules.Workflow{}, Rules.Strict{}, 1, [1], True{}}
    ],
    [
      Rules.ImportEdge{2, 1, Rules.Flow{}, Rules.Entry{}}
    ],
    [

    ]
  }
