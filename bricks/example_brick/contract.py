"""Typed, versioned boundary and ownership declarations for this brick."""

from typing import TypedDict


CONTRACT_VERSION = 1

# The enforcement class this brick declares for itself: "strict" (the regular
# brick), "pure" (output is a function of input alone), or "workflow" (invoked
# as a whole, never depended on). A lane only adds rules. Omitting it means
# "strict".
LANE = "strict"

# True only when the same input always gives the same output. The runtime then
# stores a hash of each output instead of the output, because a replay can
# compute it again. A model, a sampler or anything with hidden state is False.
# A wrong True loses data that cannot be recovered, so False is the default.
DETERMINISTIC = False

# Map sibling brick names to "eventual" or "orchestrated".
SIBLING_DEPENDENCIES: dict[str, str] = {}

# Stable identifiers for application state owned exclusively by this brick.
OWNED_STATE: tuple[str, ...] = ()

# This file is human-only: no agent loop may change it. Inputs and outputs must
# be JSON values, because the runtime records them.


class BrickInput(TypedDict):
    """Input accepted by run(). Replace with domain fields."""


class BrickOutput(TypedDict):
    """Output returned by run(). Replace with domain fields."""
