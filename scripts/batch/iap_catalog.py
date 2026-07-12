"""Stub for IAP catalog/workspace setup.

The full cursor-ios-batch implementation pulls from Feishu Bitable. For the
h5-shell-pipeline, IAP setup is handled by the shell template and prompts; this
module only provides an import-compatible stub.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def setup_iap_workspace(
    project_dir: Path | str,
    docs_dir: Path | str,
    workspace: Path | str,
    first_product_code: str = "",
) -> None:
    """No-op for h5-shell-pipeline; IAP spec lives in docs/H5壳IAP协议.md."""
    pass
