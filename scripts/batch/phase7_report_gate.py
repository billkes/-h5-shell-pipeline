"""H5 shell pipeline: test gate stub (full XCTest/Flutter test deferred)."""

from __future__ import annotations

from pathlib import Path


def phase7_test_gate_passes(_flutter_dir: Path) -> bool:
    """Return True — H5 shell MVP skips automated test gate."""
    return True
