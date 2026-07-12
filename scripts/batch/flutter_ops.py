"""Stub for Flutter project detection used by workspace.py."""

from __future__ import annotations

from pathlib import Path


def find_flutter_project(workspace: Path | str) -> Path | None:
    """h5-shell-pipeline does not operate on Flutter workspaces directly."""
    return None
