"""Stub for ui-ux-pro-max skill resolution used by workspace.py."""

from __future__ import annotations

from pathlib import Path

from batch.config import BatchConfig


def resolve_uupm_package_dir(cfg: BatchConfig) -> Path:
    raise RuntimeError("ui-ux-pro-max skill 未在 h5-shell-pipeline 中配置")


def resolve_uupm_skill_repo_root(cfg: BatchConfig) -> Path | None:
    raise RuntimeError("ui-ux-pro-max skill 未在 h5-shell-pipeline 中配置")
