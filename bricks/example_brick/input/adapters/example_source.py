"""Replace with an adapter for one external source."""


def fetch(request: dict, ctx: dict) -> dict:
    """Fetch data from the source.

    The call goes through the run context's io, never directly: in production
    the io makes the call and records it; in evaluation it replays the record.
    Translate the raw response into this brick's own types after the call.
    """
    return ctx["io"].external("example_source", request, _fetch_live)


def _fetch_live(request: dict) -> dict:
    """Replace with the real external call."""
    raise NotImplementedError
