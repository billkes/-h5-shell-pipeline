"""Stub for UI compliance helpers used by workspace.py.

h5-shell-pipeline does not use the cursor-ios-batch UI compliance/IAP spec copy
flow; this module provides import-compatible fallbacks.
"""

from __future__ import annotations

from pathlib import Path

IAP_SOURCE = "data/static/iap_spec.json"


def copy_iap_spec_file(src: Path | str, workspace: Path | str) -> None:
    """No-op if the source file does not exist."""
    src_path = Path(src)
    if not src_path.is_file():
        return
    dest = Path(workspace) / src_path.name
    dest.write_bytes(src_path.read_bytes())
