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


def h5_shell_retry_slot_issues(
    flutter_dir: Path,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> list[str]:
    """Warn when h5_shell Flutter retry illustration slot is missing or stub-sized."""
    ws = _workspace_root(flutter_dir)
    if not _is_h5_shell_workspace(ws):
        return []

    lock_path = ws / "本包维度锁.json"
    if not lock_path.is_file():
        return ["h5_shell retry slot：缺少 本包维度锁.json"]
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["h5_shell retry slot：本包维度锁.json 解析失败"]

    layout = layout_from_lock(lock if isinstance(lock, dict) else None)
    ps = (lock or {}).get("programmingStyle") or {}
    slots = []
    if isinstance(ps, dict) and ps.get("assetSlots"):
        slots = ps.get("assetSlots") or []
    else:
        slots = layout.get("assetSlots") or []
    retry_slots = [
        s
        for s in slots
        if isinstance(s, dict)
        and (
            str(s.get("role") or "").startswith("retry")
            or str(s.get("slot") or "").startswith("retry")
        )
    ]
    if not retry_slots:
        return ["h5_shell retry slot：assetSlots 未登记 retry_illustration"]

    issues: list[str] = []
    for slot in retry_slots:
        rel = str(slot.get("path") or "").strip()
        if not rel:
            issues.append("h5_shell retry slot：slot 缺少 path")
            continue
        path = flutter_dir / rel
        if not path.is_file():
            issues.append(f"h5_shell retry slot：缺失 → {rel}")
            continue
        try:
            size = path.stat().st_size
        except OSError:
            issues.append(f"h5_shell retry slot：无法读取 → {rel}")
            continue
        if size < min_bytes:
            issues.append(
                f"h5_shell retry slot：过小 ({size}B < {min_bytes}B) → {rel}"
            )
    return issues


def phase9_asset_gate_issues(
    flutter_dir: Path,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> list[str]:
    """Human-readable blockers for live ``image_prompts.json`` raster assets."""
    issues = verify_manifest_assets(flutter_dir, min_bytes=min_bytes)
    issues.extend(verify_manifest_duplicate_md5(flutter_dir))
    issues.extend(h5_shell_retry_slot_issues(flutter_dir, min_bytes=min_bytes))
    return issues


def phase9_asset_gate_passes(
    flutter_dir: Path,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> bool:
    """Return True when every live manifest slot is present, sized, and unique MD5."""
    return not phase9_asset_gate_issues(flutter_dir, min_bytes=min_bytes)
