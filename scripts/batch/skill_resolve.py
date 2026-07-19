"""Unified ui-ux-pro-max-skill path resolution and integration flags."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from batch.config import BatchConfig

UUPM_PACKAGE_SUFFIX = Path("src/ui-ux-pro-max")
UUPM_SCRIPTS_SUFFIX = UUPM_PACKAGE_SUFFIX / "scripts"
SUBSKILL_NAMES: tuple[str, ...] = ("brand", "design-system", "design", "ui-styling")

DEFAULT_UUPM_INTEGRATIONS: dict[str, bool] = {
    "enrich_domains": True,
    "page_overrides": True,
    "token_sync": True,
    "icon_brief": True,
    "motion_css": True,
    "sibling_skills_link": True,
}


def _bool_integration(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    return default


def load_uupm_integrations(cfg: BatchConfig) -> dict[str, bool]:
    """Merge config.yaml uupm.integrations with defaults."""
    out = dict(DEFAULT_UUPM_INTEGRATIONS)
    yaml_path = cfg.config_dir / "config.yaml"
    if yaml_path.is_file():
        try:
            import yaml

            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            uupm = data.get("uupm") if isinstance(data, dict) else None
            if isinstance(uupm, dict):
                raw = uupm.get("integrations")
                if isinstance(raw, dict):
                    for key, default in DEFAULT_UUPM_INTEGRATIONS.items():
                        if key in raw:
                            out[key] = _bool_integration(raw[key], default)
        except Exception:
            pass
    extra = getattr(cfg, "uupm_integrations", None)
    if isinstance(extra, dict):
        for key, default in DEFAULT_UUPM_INTEGRATIONS.items():
            if key in extra:
                out[key] = _bool_integration(extra[key], default)
    return out


def integration_enabled(cfg: BatchConfig, key: str) -> bool:
    return load_uupm_integrations(cfg).get(key, DEFAULT_UUPM_INTEGRATIONS.get(key, False))


def _uupm_skill_repo_candidates(cfg: BatchConfig) -> list[Path]:
    import os

    candidates: list[Path] = []
    cfg_dir = (cfg.uupm_skill_dir or "").strip()
    if cfg_dir:
        candidates.append(Path(cfg_dir).expanduser())
    env = (os.environ.get("UUPM_SKILL_DIR") or "").strip()
    if env:
        candidates.append(Path(env).expanduser())
    yaml_path = cfg.config_dir / "config.yaml"
    if yaml_path.is_file():
        try:
            import yaml

            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            uupm = data.get("uupm") if isinstance(data, dict) else None
            if isinstance(uupm, dict):
                raw = str(uupm.get("skill_dir") or "").strip()
                if raw:
                    candidates.append(Path(raw).expanduser())
        except Exception:
            pass
    for base in (cfg.project_dir.parent, cfg.project_dir.parent.parent):
        candidates.append(base / "ui-ux-pro-max-skill")
    seen: set[str] = set()
    ordered: list[Path] = []
    for root in candidates:
        key = str(root.resolve()) if root.exists() else str(root)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(root)
    return ordered


def _scripts_dir_from_root(root: Path) -> Path | None:
    nested = root / UUPM_SCRIPTS_SUFFIX
    if nested.is_dir() and (nested / "search.py").is_file():
        return nested
    if root.is_dir() and (root / "search.py").is_file():
        return root
    return None


def resolve_uupm_scripts_dir(cfg: BatchConfig) -> Path:
    for root in _uupm_skill_repo_candidates(cfg):
        scripts = _scripts_dir_from_root(root)
        if scripts is not None:
            return scripts
    raise RuntimeError(
        "找不到 ui-ux-pro-max-skill：请设置 config.yaml → uupm.skill_dir "
        "或环境变量 UUPM_SKILL_DIR（指向 ui-ux-pro-max-skill 仓库根目录）"
    )


def resolve_uupm_package_dir(cfg: BatchConfig) -> Path:
    scripts = resolve_uupm_scripts_dir(cfg)
    if scripts.name == "scripts" and scripts.parent.is_dir():
        return scripts.parent
    return scripts


def resolve_skill_repo_root(cfg: BatchConfig) -> Path | None:
    pkg = resolve_uupm_package_dir(cfg)
    if pkg.name == "ui-ux-pro-max" and pkg.parent.name == "src":
        return pkg.parent.parent
    for root in _uupm_skill_repo_candidates(cfg):
        if _scripts_dir_from_root(root) is not None:
            return root
    return None


def resolve_subskill_dir(cfg: BatchConfig, name: str) -> Path | None:
    """Return ``.claude/skills/{name}`` under skill repo root."""
    if name not in SUBSKILL_NAMES:
        return None
    root = resolve_skill_repo_root(cfg)
    if root is None:
        return None
    path = root / ".claude" / "skills" / name
    return path if path.is_dir() else None


def inject_uupm_scripts(cfg: BatchConfig) -> Path:
    scripts_dir = resolve_uupm_scripts_dir(cfg)
    scripts = str(scripts_dir.resolve())
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    return scripts_dir
