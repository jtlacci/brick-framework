#!/usr/bin/env python3
"""Prove that the strict type gate rejects known-bad brick connections."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tools/tests/fixtures/typing/bad_connections.py"


def main() -> int:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--no-incremental",
            "--config-file",
            str(ROOT / "mypy.ini"),
            str(FIXTURE),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    expected = sorted(("[arg-type]", "[typeddict-item]"))
    observed = sorted(re.findall(r"\[[-a-z]+\]$", output, flags=re.MULTILINE))
    if result.returncode != 1 or observed != expected:
        print(output, file=sys.stderr, end="")
        print(
            f"expected mypy exit 1 and error codes {expected}; "
            f"observed exit {result.returncode} and {observed}",
            file=sys.stderr,
        )
        return 1
    print("typing regression fixture rejected the expected bad connections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
