"""Lightweight brand asset validation (WARN-only)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from batch.skill_resolve import integration_enabled, resolve_subskill_dir

if TYPE_CHECKING:
    from batch.config import BatchConfig

_ICON_MIN = 1024
_ICON_MAX_BYTES = 5 * 1024 * 1024


def _find_app_icons(workspace: Path) -> list[Path]:
    patterns = (
        "AppIcon*.png",
        "AppIcon*.jpg",
        "AppIcon*.jpeg",
        "icon*.png",
        "assets/**/AppIcon*.png",
        "ios/**/AppIcon*.png",
    )
    found: list[Path] = []
    for pattern in patterns:
        for path in workspace.glob(pattern):
            if path.is_file() and path not in found:
                found.append(path)
    return found[:8]


def _python_validate(asset: Path) -> list[str]:
    issues: list[str] = []
    if asset.stat().st_size > _ICON_MAX_BYTES:
        issues.append(f"{asset.name}: file size exceeds 5MB")
    try:
        from PIL import Image

        with Image.open(asset) as img:
            w, h = img.size
            if w < _ICON_MIN or h < _ICON_MIN:
                issues.append(f"{asset.name}: dimensions {w}x{h} below {_ICON_MIN}px")
            if w != h:
                issues.append(f"{asset.name}: non-square icon ({w}x{h})")
    except ImportError:
        pass
    except OSError as exc:
        issues.append(f"{asset.name}: unreadable image ({exc})")
    return issues


def _node_validate(cfg: BatchConfig, asset: Path) -> dict[str, Any] | None:
    brand_dir = resolve_subskill_dir(cfg, "brand")
    if brand_dir is None:
        return None
    script = brand_dir / "scripts" / "validate-asset.cjs"
    if not script.is_file():
        return None
    try:
        proc = subprocess.run(
            ["node", str(script), str(asset), "--json"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        data = json.loads(proc.stdout)
        return data if isinstance(data, dict) else None
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None


def run_brand_check(*, cfg: BatchConfig, workspace: Path) -> Path:
    """Write skill-adapt/brand-check.json (WARN-only, never blocks pipeline)."""
    out_path = workspace / "skill-adapt" / "brand-check.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not integration_enabled(cfg, "token_sync"):
        out_path.write_text(json.dumps({"skipped": True, "warnings": []}, indent=2) + "\n", encoding="utf-8")
        return out_path

    assets = _find_app_icons(workspace)
    warnings: list[str] = []
    details: list[dict[str, Any]] = []

    for asset in assets:
        py_issues = _python_validate(asset)
        node_result = _node_validate(cfg, asset)
        entry: dict[str, Any] = {
            "path": asset.relative_to(workspace).as_posix(),
            "pythonIssues": py_issues,
        }
        if node_result is not None:
            entry["nodeValidation"] = node_result
            for issue in node_result.get("issues") or []:
                if isinstance(issue, str):
                    warnings.append(f"{asset.name}: {issue}")
        for issue in py_issues:
            warnings.append(f"{asset.name}: {issue}")
        details.append(entry)

    payload = {
        "assetCount": len(assets),
        "warnings": warnings,
        "assets": details,
        "status": "warn" if warnings else "ok",
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def brand_check_warnings(workspace: Path) -> list[str]:
    """Return WARN strings for plan.gate (non-blocking)."""
    path = workspace / "skill-adapt" / "brand-check.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["brand-check.json 无法解析"]
    if not isinstance(data, dict):
        return []
    return [f"[brand] {w}" for w in (data.get("warnings") or []) if str(w).strip()]
