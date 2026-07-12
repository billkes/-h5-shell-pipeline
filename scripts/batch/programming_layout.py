"""Stub for programming layout resolution used by workspace.py."""

from __future__ import annotations

from typing import Any


def layout_from_lock(lock: dict[str, Any]) -> dict[str, Any]:
    """Return a minimal layout for h5-shell-pipeline."""
    return {"assetRoots": ["assets/images/"]}
