"""Stub for dimension lock resolution used by workspace.py."""

from __future__ import annotations

from pathlib import Path


def resolve_dimension_lock(workspace: Path | str) -> dict:
    """Return an empty lock for h5-shell-pipeline."""
    return {}
