"""Canonical placeholder AppIcon + launch_placeholder for H5 native shells."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from batch.image_placeholders import palette_from_color_tokens, write_placeholder

APP_ICON_SIZE = (1024, 1024)
LAUNCH_PLACEHOLDER_SIZE = (1125, 2436)

# Hathoo-OC reference binaries accidentally baked into early oc_shell templates.
_FACTORY_ICON_BYTES = frozenset({104_895})
_FACTORY_LAUNCH_BYTES = frozenset({192_901})


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
            launch = str(data.get("launchPlaceholderAsset") or "")
            m = re.search(r"assets/([a-z0-9]+)_launch/", launch)
            if m:
                return m.group(1)
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


def write_launch_placeholder_png(dest: Path, *, palette: list[tuple[int, int, int]] | None = None) -> None:
    write_placeholder(
        dest,
        role="launch_placeholder",
        basename=dest.name,
        palette_anchors=palette or palette_from_color_tokens(None),
        size=LAUNCH_PLACEHOLDER_SIZE,
    )


def apply_shell_placeholders(
    workspace: Path,
    *,
    prefix: str = "",
    force: bool = False,
) -> list[str]:
    """Write watermark placeholders into native AppIcon + launch imagesets and H5 launch asset."""
    ws = workspace.resolve()
    prefix = (prefix or prefix_from_workspace(ws)).strip()
    palette = _palette_from_workspace(ws)
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
    launch_png: Path | None = None
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
        write_launch_placeholder_png(dest, palette=palette)
        rel = str(dest.relative_to(ws))
        changed.append(rel)
        launch_png = dest

    if prefix:
        h5_dest = ws / "h5" / "assets" / f"{prefix}_launch" / "launch_placeholder.png"
        if launch_png and launch_png.is_file():
            h5_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(launch_png, h5_dest)
            changed.append(str(h5_dest.relative_to(ws)))
        else:
            if h5_dest.is_file() and not force and not _looks_like_factory_asset(h5_dest):
                pass
            else:
                write_launch_placeholder_png(h5_dest, palette=palette)
                changed.append(str(h5_dest.relative_to(ws)))

    return changed


def collect_placeholder_violations(workspace: Path) -> list[str]:
    """Flag missing launch/icon assets or factory-copied binaries."""
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

    launch_sets = [
        p
        for p in ws.rglob("*.imageset")
        if "/build/" not in str(p) and "launch" in p.name.lower()
    ]
    if not launch_sets:
        issues.append("缺少 launch_placeholder imageset")
    for img_set in launch_sets:
        pngs = list(img_set.glob("*.png"))
        if not pngs:
            issues.append(f"Launch 占位图缺失: {img_set.relative_to(ws)}")
            continue
        for png in pngs:
            if _looks_like_factory_asset(png):
                issues.append(
                    f"Launch 占位仍为厂包真图（须占位）: {png.relative_to(ws)}"
                )

    prefix = prefix_from_workspace(ws)
    if prefix:
        h5_launch = ws / "h5" / "assets" / f"{prefix}_launch" / "launch_placeholder.png"
        if not h5_launch.is_file():
            issues.append(f"H5 launch 占位缺失: {h5_launch.relative_to(ws)}")
        elif _looks_like_factory_asset(h5_launch):
            issues.append(f"H5 launch 仍为厂包真图: {h5_launch.relative_to(ws)}")

    return issues
