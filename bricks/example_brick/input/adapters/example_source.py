"""Replace with an adapter for one external source."""


def fetch(request: dict, run_context: dict) -> dict:
    """Fetch data from the external source."""
    raise NotImplementedError
