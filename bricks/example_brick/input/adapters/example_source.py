"""Replace with an adapter for one external source."""

from ..evidence import load_example, save_example


def fetch(request: dict, run_context: dict, *, case: str = "default") -> dict:
    """Fetch data using this brick's saved, fresh, or save mode."""
    mode = run_context["mode"]
    if mode == "saved":
        example = load_example("example_source", case, request)
        if "error" in example:
            raise RuntimeError(f"saved adapter error: {example['error']}")
        return example["response"]

    try:
        response = _fetch_live(request)
    except Exception as exc:
        if mode == "save":
            save_example(
                "example_source",
                case,
                run_context["run_id"],
                request,
                error={"type": type(exc).__name__},
                max_bytes=run_context["config"]["limits"]["max_evidence_bytes"],
            )
        raise

    if mode == "save":
        save_example(
            "example_source",
            case,
            run_context["run_id"],
            request,
            response=response,
            max_bytes=run_context["config"]["limits"]["max_evidence_bytes"],
        )
    return response


def _fetch_live(request: dict) -> dict:
    """Replace with the real external call."""
    raise NotImplementedError
