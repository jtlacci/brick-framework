"""Small, Git-stable saved-example storage for this brick.

Copy this file with the brick boilerplate. It deliberately has no dependency
outside the Python standard library and no knowledge of the runner.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any


DATA_DIR = Path(__file__).with_name("data")
DEFAULT_MAX_BYTES = 16_384
_SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_REDACTED_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "cookie",
    "cookies",
    "headers",
    "password",
    "refresh_token",
    "secret",
    "set-cookie",
    "token",
    "x-api-key",
}
_MISSING = object()


class EvidenceError(RuntimeError):
    """Saved evidence is absent, unsafe, invalid, or does not match."""


def load_example(adapter: str, case: str, request: dict[str, Any]) -> dict[str, Any]:
    """Load a saved example and require its request to match exactly."""
    path = _example_path(adapter, case)
    if not path.is_file():
        raise EvidenceError(f"saved example does not exist: {path}")

    record = json.loads(path.read_text(encoding="utf-8"))
    normalized_request = _redact(_normalize(request))
    if record.get("request") != normalized_request:
        raise EvidenceError(f"saved request does not match case {adapter}/{case}")
    if ("response" in record) == ("error" in record):
        raise EvidenceError(f"saved example must contain response or error: {path}")
    return record


def save_example(
    adapter: str,
    case: str,
    capture_run_id: str,
    request: dict[str, Any],
    *,
    response: Any = _MISSING,
    error: Any = _MISSING,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Path:
    """Atomically replace one canonical, size-limited saved example."""
    if (response is _MISSING) == (error is _MISSING):
        raise EvidenceError("provide exactly one of response or error")

    record: dict[str, Any] = {
        "adapter": adapter,
        "capture_run_id": capture_run_id,
        "case": case,
        "request": _redact(_normalize(request)),
        "schema_version": 1,
    }
    if response is not _MISSING:
        record["response"] = _redact(_normalize(response))
    else:
        record["error"] = _redact(_normalize(error))

    payload = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(payload) > max_bytes:
        raise EvidenceError(
            f"saved evidence is {len(payload)} bytes; limit is {max_bytes} bytes"
        )

    path = _example_path(adapter, case)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".evidence-", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path


def _example_path(adapter: str, case: str) -> Path:
    for label, value in (("adapter", adapter), ("case", case)):
        if not _SAFE_NAME.fullmatch(value):
            raise EvidenceError(f"unsafe {label} name: {value!r}")
    return DATA_DIR / adapter / f"{case}.json"


def _normalize(value: Any) -> Any:
    """Return the JSON representation or raise a useful evidence error."""
    try:
        return json.loads(json.dumps(value, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise EvidenceError("evidence must be JSON-serializable") from exc


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if key.lower() in _REDACTED_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
