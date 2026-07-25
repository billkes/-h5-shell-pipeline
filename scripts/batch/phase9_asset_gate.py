"""Phase 9/10 asset gate — manifest paths must be real, non-stub, non-duplicate."""

from __future__ import annotations

import json
from pathlib import Path

from batch.image_prompts_sync import (
    MIN_RENDERED_ASSET_BYTES,
    verify_manifest_assets,
    verify_manifest_duplicate_md5,
)
from batch.pack_type import is_h5_shell
from batch.programming_layout import layout_from_lock

REQUIRED_H5_SHELL_SLOTS: frozenset[str] = frozenset(
    {
        "logo",
        "launch_light",
        "launch_dark",
        "global_bg_light",
        "global_bg_dark",
        "retry_illustration",
    }
)


def _workspace_root(flutter_dir: Path) -> Path:
    parent = flutter_dir.parent
    if (parent / "本包登记信息.json").is_file() or (parent / "本包维度锁.json").is_file():
        return parent
    return flutter_dir


def _is_h5_shell_workspace(ws: Path) -> bool:
    reg = ws / "本包登记信息.json"
    if reg.is_file():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict) and is_h5_shell(str(data.get("packType") or "")):
            return True
    lock_path = ws / "本包维度锁.json"
    if lock_path.is_file():
        try:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            lock = {}
        ps = (lock or {}).get("programmingStyle") or {}
        if isinstance(ps, dict) and ps.get("h5VaultPattern"):
            return True
    return False


def _asset_slots_from_workspace(ws: Path) -> list[dict]:
    lock_path = ws / "本包维度锁.json"
    if not lock_path.is_file():
        return []
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(lock, dict):
        return []
    layout = layout_from_lock(lock)
    ps = lock.get("programmingStyle") or {}
    if isinstance(ps, dict) and ps.get("assetSlots"):
        slots = ps.get("assetSlots") or []
    else:
        slots = layout.get("assetSlots") or []
    return [s for s in slots if isinstance(s, dict)]


def h5_shell_raster_slot_issues(
    flutter_dir: Path,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> list[str]:
    """Block when h5_shell fixed raster slots are missing or stub-sized."""
    ws = _workspace_root(flutter_dir)
    if not _is_h5_shell_workspace(ws):
        return []

    slots = _asset_slots_from_workspace(ws)
    if not slots and not (ws / "本包维度锁.json").is_file():
        return ["h5_shell raster：缺少 本包维度锁.json"]

    by_slot = {
        str(s.get("slot") or "").strip(): s
        for s in slots
        if str(s.get("slot") or "").strip()
    }
    issues: list[str] = []
    missing = sorted(REQUIRED_H5_SHELL_SLOTS - set(by_slot))
    if missing:
        issues.append(
            "h5_shell raster：assetSlots 缺少 " + ", ".join(missing)
        )

    check_slots = [by_slot[k] for k in sorted(by_slot) if k in REQUIRED_H5_SHELL_SLOTS]
    if not check_slots:
        # Fall back to legacy retry-only detection
        check_slots = [
            s
            for s in slots
            if str(s.get("role") or "").startswith("retry")
            or str(s.get("slot") or "").startswith("retry")
        ]
        if not check_slots:
            issues.append("h5_shell raster：assetSlots 未登记 shell rasters")
            return issues

    for slot in check_slots:
        rel = str(slot.get("path") or "").strip()
        label = str(slot.get("slot") or slot.get("role") or rel or "?")
        if not rel:
            issues.append(f"h5_shell raster：{label} 缺少 path")
            continue
        path = flutter_dir / rel
        if not path.is_file():
            issues.append(f"h5_shell raster：缺失 → {rel}")
            continue
        try:
            size = path.stat().st_size
        except OSError:
            issues.append(f"h5_shell raster：无法读取 → {rel}")
            continue
        if size < min_bytes:
            issues.append(
                f"h5_shell raster：过小 ({size}B < {min_bytes}B) → {rel}"
            )
    return issues


def h5_shell_retry_slot_issues(
    flutter_dir: Path,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> list[str]:
    """Backward-compatible alias for ``h5_shell_raster_slot_issues``."""
    return h5_shell_raster_slot_issues(flutter_dir, min_bytes=min_bytes)


def phase9_asset_gate_issues(
    flutter_dir: Path,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> list[str]:
    """Human-readable blockers for live ``image_prompts.json`` raster assets."""
    issues = verify_manifest_assets(flutter_dir, min_bytes=min_bytes)
    issues.extend(verify_manifest_duplicate_md5(flutter_dir))
    issues.extend(h5_shell_raster_slot_issues(flutter_dir, min_bytes=min_bytes))
    return issues


def phase9_asset_gate_passes(
    flutter_dir: Path,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> bool:
    return not phase9_asset_gate_issues(flutter_dir, min_bytes=min_bytes)
