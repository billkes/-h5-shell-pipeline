"""Native app bundle raster for h5_oc_shell / h5_swift_shell (mediaServe)."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_vite_scaffold import resolve_prefix
from batch.pack_type import is_native_ios_runtime

REGISTER_FILE = "本包登记信息.json"
NATIVE_SEED_BUNDLE_SUBDIR = "SeedBundle"
LEGACY_WORKSPACE_ASSETS_IMG = Path("assets") / "img"
LEGACY_H5_VAULT_SUFFIX = "_vault"
_RASTER_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})


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


def native_ios_app_src_dir(project: Path) -> Path | None:
    """Return ios/{AppName}/ native source root when present."""
    ws = project.resolve()
    ios_root = ws / "ios"
    if not ios_root.is_dir():
        return None
    for xproj in sorted(ws.glob("*.xcodeproj")):
        candidate = ios_root / xproj.stem
        if candidate.is_dir():
            return candidate
    dirs = sorted(p for p in ios_root.iterdir() if p.is_dir() and not p.name.startswith("."))
    if len(dirs) == 1:
        return dirs[0]
    return None


def native_bundled_img_dir(project: Path) -> Path | None:
    """On-disk seed rasters for OC/Swift: ios/{AppName}/SeedBundle/."""
    if not requires_native_bundled_media(project):
        return None
    app = native_ios_app_src_dir(project)
    if not app:
        return None
    return app / NATIVE_SEED_BUNDLE_SUBDIR


def legacy_h5_vault_dir(project: Path, prefix: str = "") -> Path:
    p = (prefix or resolve_prefix(project) or "app").strip().lower()
    return project / "h5" / "assets" / f"{p}{LEGACY_H5_VAULT_SUFFIX}"


def _dir_has_raster_files(path: Path) -> bool:
    if not path.is_dir():
        return False
    return any(
        p.is_file() and p.suffix.lower() in _RASTER_SUFFIXES for p in path.iterdir()
    )


def collect_native_bundled_media_violations(project: Path) -> list[str]:
    """Hard gate: OC/Swift seed rasters in SeedBundle; forbid h5 vault & assets/img dupes."""
    if not requires_native_bundled_media(project):
        return []

    issues: list[str] = []
    prefix = resolve_prefix(project) or "app"
    ws = project.resolve()

    legacy = legacy_h5_vault_dir(project, prefix)
    if legacy.is_dir() and any(legacy.iterdir()):
        issues.append(
            f"禁止 h5/assets/{prefix}_vault/ 栅格副本；配图须打入 Native 安装包 "
            f"(ios/{{AppName}}/{NATIVE_SEED_BUNDLE_SUBDIR}/)"
        )

    if _dir_has_raster_files(ws / LEGACY_WORKSPACE_ASSETS_IMG):
        issues.append(
            "禁止 workspace 根 assets/img/ 栅格副本；seed 配图须仅放在 "
            f"ios/{{AppName}}/{NATIVE_SEED_BUNDLE_SUBDIR}/（Xcode Copy Bundle Resources）"
        )

    for xproj in sorted(ws.glob("*.xcodeproj")):
        legacy_app_img = ws / xproj.stem / LEGACY_WORKSPACE_ASSETS_IMG
        if _dir_has_raster_files(legacy_app_img):
            issues.append(
                f"禁止 {xproj.stem}/assets/img/ 栅格副本；seed 配图须仅放在 "
                f"ios/{xproj.stem}/{NATIVE_SEED_BUNDLE_SUBDIR}/"
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
