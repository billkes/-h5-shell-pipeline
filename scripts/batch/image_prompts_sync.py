"""Sync raster assets with ``image_prompts.json`` after Agent phases.

Repairs missing or stub-sized PNGs (< ``MIN_RENDERED_ASSET_BYTES``) so Phase 6
stats and UI no longer show zero-byte / 99-byte agent stubs.
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path

MIN_RENDERED_ASSET_BYTES = 5120


@dataclass
class ImagePromptSyncReport:
    """Outcome of a manifest-driven asset sync pass."""

    total_entries: int = 0
    already_ok: int = 0
    repaired: int = 0
    failed: list[str] = field(default_factory=list)

    @property
    def needs_attention(self) -> bool:
        return bool(self.failed) or self.repaired > 0


def load_live_manifest_entries(flutter_dir: Path) -> list[dict]:
    """Return non-skipped entries from ``image_prompts.json``."""
    manifest_path = flutter_dir / "image_prompts.json"
    if not manifest_path.is_file():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    entries = data.get("entries") or []
    live: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("skipped"):
            continue
        rel = str(entry.get("path") or "").strip()
        if rel:
            live.append(entry)
    return live


def entry_needs_sync(
    flutter_dir: Path,
    entry: dict,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> bool:
    rel = str(entry.get("path") or "").strip()
    if not rel:
        return False
    path = flutter_dir / rel
    if not path.is_file():
        return True
    return path.stat().st_size < min_bytes


def count_manifest_resource_stats(
    flutter_dir: Path,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> tuple[int, int]:
    """Count live manifest entries and how many are missing or stub-sized."""
    entries = load_live_manifest_entries(flutter_dir)
    if not entries:
        return 0, 0
    placeholder = 0
    for entry in entries:
        if entry_needs_sync(flutter_dir, entry, min_bytes=min_bytes):
            placeholder += 1
    return len(entries), placeholder


def _load_render_entry(project_dir: Path):
    script = project_dir / "scripts" / "render_image_prompts_local.py"
    if not script.is_file():
        raise FileNotFoundError(f"render script missing: {script}")
    spec = importlib.util.spec_from_file_location(
        "render_image_prompts_local",
        script,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load render script: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    render_fn = getattr(module, "_render_entry", None)
    if render_fn is None:
        raise RuntimeError("_render_entry not found in render script")
    return render_fn


def sync_image_prompt_assets(
    flutter_dir: Path,
    project_dir: Path,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> ImagePromptSyncReport:
    """Render PNGs for manifest paths that are missing or smaller than ``min_bytes``."""
    manifest_path = flutter_dir / "image_prompts.json"
    report = ImagePromptSyncReport()
    if not manifest_path.is_file():
        return report

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.failed.append(f"invalid image_prompts.json: {exc}")
        return report

    app = str(data.get("app") or flutter_dir.name)
    entries = load_live_manifest_entries(flutter_dir)
    report.total_entries = len(entries)
    if not entries:
        return report

    try:
        render_entry = _load_render_entry(project_dir)
    except (FileNotFoundError, RuntimeError) as exc:
        report.failed.append(str(exc))
        return report

    for entry in entries:
        rel = str(entry.get("path") or "").strip()
        out_path = flutter_dir / rel
        if not entry_needs_sync(flutter_dir, entry, min_bytes=min_bytes):
            report.already_ok += 1
            continue
        try:
            render_entry(app, entry, out_path)
            if out_path.is_file() and out_path.stat().st_size >= min_bytes:
                report.repaired += 1
            else:
                report.failed.append(f"{rel}(render too small)")
        except OSError as exc:
            report.failed.append(f"{rel}({exc})")

    return report


def verify_manifest_assets(
    flutter_dir: Path,
    *,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
) -> list[str]:
    """Human-readable issues for live ``image_prompts.json`` raster paths."""
    issues: list[str] = []
    entries = load_live_manifest_entries(flutter_dir)
    if not entries:
        return issues
    missing = 0
    stub = 0
    for entry in entries:
        rel = str(entry.get("path") or "").strip()
        path = flutter_dir / rel
        if not path.is_file():
            missing += 1
            continue
        if path.stat().st_size < min_bytes:
            stub += 1
    if missing:
        issues.append(
            f"image_prompts 配图缺失: {missing}/{len(entries)} 个路径无文件"
        )
    if stub:
        issues.append(
            f"image_prompts 配图过小(<{min_bytes}B): {stub}/{len(entries)} 个疑似 stub"
        )
    return issues


def verify_manifest_duplicate_md5(flutter_dir: Path) -> list[str]:
    """Flag uniform placeholder PNGs (same MD5 across multiple live manifest paths)."""
    import hashlib
    from collections import defaultdict

    entries = load_live_manifest_entries(flutter_dir)
    if len(entries) < 2:
        return []

    by_hash: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        rel = str(entry.get("path") or "").strip()
        path = flutter_dir / rel
        if not path.is_file():
            continue
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        by_hash[digest].append(rel)

    dup_groups = {h: paths for h, paths in by_hash.items() if len(paths) > 1}
    if not dup_groups:
        return []

    total = sum(len(v) for v in dup_groups.values())
    sample = next(iter(dup_groups.values()))
    return [
        f"image_prompts 配图 MD5 重复: {len(dup_groups)} 组 / {total} 个文件"
        f"（例: {sample[0]} 与 {sample[1]} 相同，疑似 uniform PLACEHOLDER）"
    ]
