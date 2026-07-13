"""Native app bundle raster for h5_oc_shell / h5_swift_shell (mediaServe)."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_vite_scaffold import resolve_prefix
from batch.pack_type import is_native_ios_runtime

REGISTER_FILE = "本包登记信息.json"
NATIVE_IMG_SUBDIR = Path("assets") / "img"
LEGACY_H5_VAULT_SUFFIX = "_vault"


def _read_register(project: Path) -> dict:
    path = project / REGISTER_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def pack_type_from_workspace(project: Path) -> str:
    reg = _read_register(project)
    return str(reg.get("packType") or "").strip()


def shell_runtime_from_workspace(project: Path) -> str:
    reg = _read_register(project)
    runtime = str(reg.get("shellRuntime") or "").strip().lower()
    if runtime:
        return runtime
    pt = pack_type_from_workspace(project)
    if pt == "h5_oc_shell":
        return "oc"
    if pt == "h5_swift_shell":
        return "swift"
    return "flutter"


def requires_native_bundled_media(project: Path) -> bool:
    return is_native_ios_runtime(pack_type_from_workspace(project))


def native_app_dir(project: Path) -> Path | None:
    """Return the Xcode app source folder (sibling to *.xcodeproj)."""
    ws = project.resolve()
    for xproj in sorted(ws.glob("*.xcodeproj")):
        candidate = ws / xproj.stem
        if candidate.is_dir():
            return candidate
    return None


def native_bundled_img_dir(project: Path) -> Path | None:
    app = native_app_dir(project)
    if not app:
        return None
    return app / NATIVE_IMG_SUBDIR


def legacy_h5_vault_dir(project: Path, prefix: str = "") -> Path:
    p = (prefix or resolve_prefix(project) or "app").strip().lower()
    return project / "h5" / "assets" / f"{p}{LEGACY_H5_VAULT_SUFFIX}"


def collect_native_bundled_media_violations(project: Path) -> list[str]:
    """Hard gate: OC/Swift shells must not keep h5/assets/{prefix}_vault raster copies."""
    if not requires_native_bundled_media(project):
        return []

    issues: list[str] = []
    prefix = resolve_prefix(project) or "app"
    legacy = legacy_h5_vault_dir(project, prefix)
    if legacy.is_dir() and any(legacy.iterdir()):
        issues.append(
            f"禁止 h5/assets/{prefix}_vault/ 栅格副本；配图须打入 Native 安装包 "
            f"({NATIVE_IMG_SUBDIR}/)"
        )

    site_root = project / "h5_site"
    if site_root.is_dir():
        for stray in site_root.rglob(f"assets/{prefix}{LEGACY_H5_VAULT_SUFFIX}"):
            if stray.is_dir() and any(stray.iterdir()):
                rel = stray.relative_to(project)
                issues.append(
                    f"禁止 h5_site 携带 vault 栅格副本: {rel}；h5_site 仅 monolith index.html"
                )
                break

    return issues
