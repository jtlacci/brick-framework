"""Replace with an adapter for one external source."""


def fetch(request: dict) -> dict:
    """Fetch data from the external source."""
    raise NotImplementedError
