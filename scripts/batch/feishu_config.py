"""Load config/feishu.yaml for lark-cli checks and future theme sync."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

from batch.config import _project_root


def default_feishu_config_path() -> Path:
    return _project_root() / "config" / "feishu.yaml"


def load_feishu_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or default_feishu_config_path()
    path = path.expanduser().resolve()
    if not path.is_file():
        print(f"  配置文件不存在: {path}")
        sys.exit(1)

    with path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    feishu = config.get("feishu")
    if not feishu or "required_scopes" not in feishu:
        print(f"  配置文件缺少 feishu.required_scopes: {path}")
        sys.exit(1)

    return config


def get_required_cli_version(config: dict[str, Any]) -> str | None:
    return config.get("lark_cli", {}).get("required_version")


def get_required_scopes(config: dict[str, Any]) -> list[dict[str, str]]:
    return list(config.get("feishu", {}).get("required_scopes") or [])


def get_base_token(config: dict[str, Any]) -> str:
    token = str(config.get("feishu", {}).get("base_token") or "").strip()
    if not token:
        raise ValueError("feishu.yaml 缺少 feishu.base_token")
    return token


def get_prod_a_task_config(config: dict[str, Any]) -> dict[str, Any]:
    prod = config.get("feishu", {}).get("prod_a_task") or {}
    if not isinstance(prod, dict):
        raise ValueError("feishu.yaml prod_a_task 必须是 object")
    return prod


def get_theme_libraries(config: dict[str, Any]) -> list[dict[str, str]]:
    libs = config.get("feishu", {}).get("theme_libraries") or []
    return [lib for lib in libs if isinstance(lib, dict)]
