"""How this brick is evaluated. Evaluation loop only: the dev agent may not change it.

The runner owns the loop. It calls build() and score() in a trusted process and
the brick's run() in a sandbox, so this file never imports or calls run(). It
may import only this brick's contract types and non-I/O standard library
modules, and it does no I/O: all data comes from the runner.
"""

from ..contract import BrickInput

# Gates: (term, operator, threshold), judged on the mean of the term over all
# cases. A candidate passes only when every gate holds. Operators: >= <= > <.
GATES: tuple[tuple[str, str, float], ...] = ()


def build(record: dict) -> BrickInput:
    """Turn one recorded run into the brick input for a case."""
    return record["input"]


def score(record: dict, output: dict | None, later: list[dict]) -> dict[str, float]:
    """Score one output and return term values.

    ``output`` is None when run() raised. ``later`` holds the records captured
    within the policy's label horizon after this case, for labels that come
    from later outcomes.
    """
    raise NotImplementedError


def generate(seed: int) -> list[dict]:
    """Return synthetic records for a brick with no real data yet.

    Each record needs at least ``input``. The runner adds the IDs, the time and
    the ``synthetic`` tag. A record may carry ``exchanges``: the external
    responses the brick will ask for, as {"name", "request", "response"}.
    """
    return []
