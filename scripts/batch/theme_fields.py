"""Stub for theme angle helpers used by csv_tasks.py.

h5-shell-pipeline does not rely on the theme-library columns for core task
parsing; these helpers provide safe fallbacks.
"""

from __future__ import annotations

from typing import Any


def format_theme_angle(row: Any) -> str:
    """Return a short English description for theme columns."""
    name = ""
    if hasattr(row, "name"):
        name = row.name
    elif isinstance(row, dict):
        name = row.get("name", "")
    full_name = ""
    if hasattr(row, "full_name"):
        full_name = row.full_name
    elif isinstance(row, dict):
        full_name = row.get("full_name", "")
    return f"{name} — {full_name}".strip(" —")


def parse_legacy_theme_angle(value: str) -> dict[str, str]:
    """No-op parser; returns empty mapping."""
    return {}


def theme_task_description(row: Any, fallback: str = "") -> str:
    """Use the theme angle as the queue description."""
    angle = format_theme_angle(row)
    return angle or fallback
