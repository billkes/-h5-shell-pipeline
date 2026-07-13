"""Canonical placeholder AppIcon + launch_placeholder for H5 native shells."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from batch.h5_site_paths import LAUNCH_PLACEHOLDER_ASSET_URI
from batch.image_placeholders import palette_from_color_tokens, write_placeholder

APP_ICON_SIZE = (1024, 1024)
LAUNCH_PLACEHOLDER_SIZE = (1125, 2436)

__all__ = [
    "APP_ICON_SIZE",
    "LAUNCH_PLACEHOLDER_ASSET_URI",
    "LAUNCH_PLACEHOLDER_SIZE",
    "apply_shell_placeholders",
    "collect_placeholder_violations",
    "find_launch_placeholder_png",
    "launch_placeholder_asset_uri",
    "legacy_h5_launch_path",
    "prefix_from_workspace",
    "remove_legacy_h5_launch_assets",
]

# Hathoo-OC reference binaries accidentally baked into early oc_shell templates.
_FACTORY_ICON_BYTES = frozenset({104_895})
_FACTORY_LAUNCH_BYTES = frozenset({192_901})

_LEGACY_H5_LAUNCH_RE = re.compile(r"^assets/[a-z0-9]+_launch/launch_placeholder\.png$")


def launch_placeholder_asset_uri() -> str:
    return LAUNCH_PLACEHOLDER_ASSET_URI


def find_launch_placeholder_png(workspace: Path) -> Path | None:
    """Resolve the canonical Native launch PNG under *launch* imageset."""
    ws = workspace.resolve()
    for img_set in ws.rglob("*.imageset"):
        if "/build/" in str(img_set) or "launch" not in img_set.name.lower():
            continue
        contents = img_set / "Contents.json"
        target_name = "launch_placeholder.png"
        if contents.is_file():
            try:
                data = json.loads(contents.read_text(encoding="utf-8"))
                for item in data.get("images") or []:
                    if isinstance(item, dict) and item.get("filename"):
                        target_name = str(item["filename"])
                        break
            except json.JSONDecodeError:
                pass
        candidate = img_set / target_name
        if candidate.is_file():
            return candidate
        pngs = sorted(img_set.glob("*.png"))
        if pngs:
            return pngs[0]
    return None


def legacy_h5_launch_path(workspace: Path, prefix: str = "") -> Path | None:
    prefix = (prefix or prefix_from_workspace(workspace)).strip()
    if not prefix:
        return None
    return workspace / "h5" / "assets" / f"{prefix}_launch" / "launch_placeholder.png"


def remove_legacy_h5_launch_assets(workspace: Path, *, prefix: str = "") -> list[str]:
    """Drop deprecated H5 launch mirror copies (Native bundle is source of truth)."""
    ws = workspace.resolve()
    prefix = (prefix or prefix_from_workspace(ws)).strip()
    removed: list[str] = []
    if not prefix:
        return removed
    legacy_dir = ws / "h5" / "assets" / f"{prefix}_launch"
    legacy_file = legacy_dir / "launch_placeholder.png"
    if legacy_file.is_file():
        legacy_file.unlink()
        removed.append(str(legacy_file.relative_to(ws)))
    if legacy_dir.is_dir() and not any(legacy_dir.iterdir()):
        legacy_dir.rmdir()
        removed.append(str(legacy_dir.relative_to(ws)))
    return removed


def _palette_from_workspace(workspace: Path) -> list[tuple[int, int, int]]:
    for name in ("本包视觉锁.json", "design-system/MASTER.md"):
        path = workspace / name
        if not path.is_file():
            continue
        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                tokens = data.get("colorTokens")
                if isinstance(tokens, dict):
                    flat: dict[str, str] = {}
                    if isinstance(tokens.get("light"), dict):
                        flat.update(tokens["light"])
                    for key in ("primary", "secondary", "accent", "backgroundDark", "surface"):
                        if key in tokens and isinstance(tokens[key], str):
                            flat[key] = tokens[key]
                if flat:
                    bg = flat.get("backgroundDark")
                    primary = flat.get("primary")
                    if isinstance(bg, str) and bg.startswith("#") and isinstance(primary, str) and primary.startswith("#"):
                        from batch.image_placeholders import hex_to_rgb

                        anchors = [hex_to_rgb(bg), hex_to_rgb(primary)]
                        accent = flat.get("accent")
                        if isinstance(accent, str) and accent.startswith("#"):
                            anchors.append(hex_to_rgb(accent))
                        return anchors
                    return palette_from_color_tokens({"light": flat})
                    return palette_from_color_tokens(tokens)
    return palette_from_color_tokens(None)


def prefix_from_workspace(workspace: Path) -> str:
    reg = workspace / "本包登记信息.json"
    if reg.is_file():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            anti = data.get("codeAntiCorrelation") or {}
            if isinstance(anti, dict):
                p = str(anti.get("dartCodePrefix") or "").strip()
                if p:
                    return p
    return ""


def _icon_filenames(icon_set: Path) -> list[str]:
    contents = icon_set / "Contents.json"
    if not contents.is_file():
        return ["AppIcon-1024.png"]
    try:
        data = json.loads(contents.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["AppIcon-1024.png"]
    names: list[str] = []
    for item in data.get("images") or []:
        if isinstance(item, dict):
            fn = str(item.get("filename") or "").strip()
            if fn:
                names.append(fn)
    return names or ["AppIcon-1024.png"]


def _looks_like_factory_asset(path: Path) -> bool:
    if not path.is_file():
        return False
    size = path.stat().st_size
    low = path.name.lower()
    if "appicon" in low or low.endswith("-1024.png"):
        return size in _FACTORY_ICON_BYTES
    if "launch" in low:
        return size in _FACTORY_LAUNCH_BYTES
    return False


def write_app_icon_placeholder(dest: Path, *, palette: list[tuple[int, int, int]] | None = None) -> None:
    write_placeholder(
        dest,
        role="app_icon",
        basename=dest.name,
        palette_anchors=palette or palette_from_color_tokens(None),
        size=APP_ICON_SIZE,
    )


def _resolve_app_display_name(workspace: Path) -> str:
    reg = workspace / "本包登记信息.json"
    if reg.is_file():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            for key in ("appName", "appDisplayName", "displayName"):
                val = str(data.get(key) or "").strip()
                if val:
                    return val
    return workspace.name.split("-")[0] or "App"


def write_launch_placeholder_png(
    dest: Path,
    *,
    palette: list[tuple[int, int, int]] | None = None,
    headline: str = "",
) -> None:
    write_placeholder(
        dest,
        role="launch_placeholder",
        basename=dest.name,
        palette_anchors=palette or palette_from_color_tokens(None),
        size=LAUNCH_PLACEHOLDER_SIZE,
        headline=headline or "Launch",
    )


def apply_shell_placeholders(
    workspace: Path,
    *,
    prefix: str = "",
    force: bool = False,
) -> list[str]:
    """Write watermark placeholders into native AppIcon + launch imageset only."""
    ws = workspace.resolve()
    prefix = (prefix or prefix_from_workspace(ws)).strip()
    palette = _palette_from_workspace(ws)
    app_name = _resolve_app_display_name(ws)
    changed: list[str] = []

    for icon_set in ws.rglob("AppIcon.appiconset"):
        if "/build/" in str(icon_set):
            continue
        for name in _icon_filenames(icon_set):
            dest = icon_set / name
            if dest.is_file() and not force and not _looks_like_factory_asset(dest):
                continue
            write_app_icon_placeholder(dest, palette=palette)
            changed.append(str(dest.relative_to(ws)))

    launch_sets = [
        p
        for p in ws.rglob("*.imageset")
        if "/build/" not in str(p) and "launch" in p.name.lower()
    ]
    for img_set in launch_sets:
        contents = img_set / "Contents.json"
        target_name = "launch_placeholder.png"
        if contents.is_file():
            try:
                data = json.loads(contents.read_text(encoding="utf-8"))
                for item in data.get("images") or []:
                    if isinstance(item, dict) and item.get("filename"):
                        target_name = str(item["filename"])
                        break
            except json.JSONDecodeError:
                pass
        dest = img_set / target_name
        if dest.is_file() and not force and not _looks_like_factory_asset(dest):
            continue
        write_launch_placeholder_png(dest, palette=palette, headline=app_name)
        changed.append(str(dest.relative_to(ws)))

    changed.extend(remove_legacy_h5_launch_assets(ws, prefix=prefix))

    from batch.native_launch_style import sync_oc_host_launch_ui

    synced = sync_oc_host_launch_ui(ws, write=True)
    if synced is not None:
        changed.append(str(synced.relative_to(ws)))

    return changed


def collect_placeholder_violations(workspace: Path) -> list[str]:
    """Flag missing launch/icon assets, factory binaries, or legacy H5 launch mirrors."""
    ws = workspace.resolve()
    issues: list[str] = []

    icon_sets = [p for p in ws.rglob("AppIcon.appiconset") if "/build/" not in str(p)]
    if not icon_sets:
        issues.append("缺少 AppIcon.appiconset")
    for icon_set in icon_sets:
        for name in _icon_filenames(icon_set):
            dest = icon_set / name
            if not dest.is_file():
                issues.append(f"AppIcon 缺失: {dest.relative_to(ws)}")
            elif _looks_like_factory_asset(dest):
                issues.append(
                    f"AppIcon 仍为厂包真图（须占位）: {dest.relative_to(ws)}"
                )

    launch_png = find_launch_placeholder_png(ws)
    if launch_png is None:
        issues.append("缺少 launch_placeholder imageset / launch_placeholder.png")
    elif _looks_like_factory_asset(launch_png):
        issues.append(f"Launch 占位仍为厂包真图（须占位）: {launch_png.relative_to(ws)}")

    reg_path = ws / "本包登记信息.json"
    if reg_path.is_file():
        try:
            reg = json.loads(reg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            reg = {}
        if isinstance(reg, dict):
            launch_uri = str(reg.get("launchPlaceholderAsset") or "").strip()
            if launch_uri and _LEGACY_H5_LAUNCH_RE.match(launch_uri):
                issues.append(
                    "launchPlaceholderAsset 仍为旧 H5 路径，须改为 "
                    f"{LAUNCH_PLACEHOLDER_ASSET_URI}"
                )
            elif launch_uri and launch_uri != LAUNCH_PLACEHOLDER_ASSET_URI:
                issues.append(
                    f"launchPlaceholderAsset 非 canonical Native URI: {launch_uri}"
                )

    prefix = prefix_from_workspace(ws)
    legacy = legacy_h5_launch_path(ws, prefix)
    if legacy and legacy.is_file():
        issues.append(
            f"冗余 H5 launch 副本应删除（Native 为唯一真源）: {legacy.relative_to(ws)}"
        )

    return issues
