"""Stub for prod-a registry validation.

The full cursor-ios-batch registry pulls from Feishu Bitable. For the
h5-shell-pipeline we keep a minimal in-memory fallback so task.csv parsing
can run without external credentials.
"""

from __future__ import annotations

from typing import Any


def load_prod_a_registry(project_dir: Any) -> dict[str, Any]:
    """Return an empty registry when no online source is configured."""
    return {"apps": []}


def validate_batch_against_registry(
    csv_rows: list[Any], registry: dict[str, Any]
) -> list[str]:
    """No-op for h5-shell-pipeline; warnings are emitted by the CLI instead."""
    return []
