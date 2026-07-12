"""h5_shell remote site paths — URL entry + deployable H5 site root (not Flutter assets)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DEFAULT_H5_SITE_ROOT = "h5_site/"
H5_PROD_HOST = "test.darin.beauty"
H5_PROD_BASE = f"https://{H5_PROD_HOST}"
DEFAULT_H5_ENTRY_URL_DEV = "http://127.0.0.1:8080/"
LAUNCH_PLACEHOLDER_SIZE = "1125x2436"


def app_slug_from_name(app_name: str) -> str:
    """App display name → URL slug (all lowercase, e.g. Gark → gark)."""
    return re.sub(r"[^a-z0-9]+", "", (app_name or "").strip().lower()) or "app"


def h5_prod_entry_url(app_slug: str) -> str:
    slug = (app_slug or "app").strip().lower()
    return f"{H5_PROD_BASE}/{slug}/"


def resolve_h5_remote_config(
    app_name: str,
    *,
    prefix: str,
    site_root: str | None = None,
) -> dict[str, Any]:
    """Registration fields for remote-first h5_shell."""
    p = (prefix or "app").strip().lower()
    if not re.fullmatch(r"[a-z]{4,6}", p):
        p = "app"
    root = (site_root or DEFAULT_H5_SITE_ROOT).strip()
    if not root.endswith("/"):
        root = f"{root}/"
    entry_name = f"{p}_entry.htm"
    entry_rel = f"{root}{entry_name}"
    slug = app_slug_from_name(app_name)
    return {
        "appSlug": slug,
        "h5SiteRoot": root,
        "h5SiteEntry": entry_name,
        "h5EntryUrlDev": DEFAULT_H5_ENTRY_URL_DEV,
        "h5EntryUrlProd": h5_prod_entry_url(slug),
        "h5EntryUrl": DEFAULT_H5_ENTRY_URL_DEV,
        "launchPlaceholderAsset": f"assets/{p}_launch/launch_placeholder.png",
        "launchPlaceholderSize": LAUNCH_PLACEHOLDER_SIZE,
        # Legacy keys → h5 site (not Flutter asset vault)
        "bundleVaultDir": root,
        "bundleEntryPath": entry_rel,
    }


def site_root_from_register(reg: dict[str, Any]) -> str:
    for key in ("h5SiteRoot", "bundleVaultDir"):
        val = str(reg.get(key) or "").strip()
        if val:
            return val.rstrip("/") + "/"
    return DEFAULT_H5_SITE_ROOT


def site_entry_rel(reg: dict[str, Any], prefix: str) -> str:
    explicit = str(reg.get("bundleEntryPath") or reg.get("h5SiteEntryPath") or "").strip()
    if explicit:
        return explicit.replace("\\", "/")
    entry_name = str(reg.get("h5SiteEntry") or "").strip()
    if not entry_name:
        p = (prefix or "app").strip().lower()
        entry_name = f"{p}_entry.htm"
    root = site_root_from_register(reg)
    return f"{root.rstrip('/')}/{entry_name}"


def site_entry_path(project: Path, reg: dict[str, Any] | None = None) -> Path:
    if reg is None:
        reg = _read_register(project)
    prefix = _resolve_prefix(project, reg)
    rel = site_entry_rel(reg, prefix)
    return project / rel


def vault_dir_path(project: Path, reg: dict[str, Any] | None = None) -> Path:
    if reg is None:
        reg = _read_register(project)
    return project / site_root_from_register(reg).rstrip("/")


def active_h5_entry_url(reg: dict[str, Any]) -> str:
    for key in ("h5EntryUrl", "h5EntryUrlDev", "h5EntryUrlProd"):
        val = str(reg.get(key) or "").strip()
        if val:
            return val
    slug = str(reg.get("appSlug") or "").strip()
    if slug:
        return h5_prod_entry_url(slug)
    return ""


def _read_register(project: Path) -> dict[str, Any]:
    path = project / "本包登记信息.json"
    if not path.is_file():
        return {}
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _resolve_prefix(project: Path, reg: dict[str, Any]) -> str:
    anti = reg.get("codeAntiCorrelation") or {}
    if isinstance(anti, dict):
        prefix = str(anti.get("dartCodePrefix") or "").strip()
        if prefix:
            return prefix
    from batch.workspace import dart_prefix

    return dart_prefix(project)


def build_h5_remote_prompt_block(app_name: str, *, prefix: str) -> str:
    cfg = resolve_h5_remote_config(app_name, prefix=prefix)
    return (
        "\n[H5 Remote Site — REQUIRED]\n"
        "- Business H5 is **deployed online** (or LAN during dev); **NOT** bundled in Flutter `pubspec` assets.\n"
        "- Shell WebView loads **`h5EntryUrl`** from 本包登记信息.json (dev → prod before release).\n"
        f"  - appSlug: `{cfg['appSlug']}`\n"
        f"  - h5EntryUrlDev: `{cfg['h5EntryUrlDev']}`\n"
        f"  - h5EntryUrlProd: `{cfg['h5EntryUrlProd']}`\n"
        f"  - h5SiteRoot: `{cfg['h5SiteRoot']}` (Implementer writes deployable site here)\n"
        f"  - h5SiteEntry: `{cfg['h5SiteEntry']}`\n"
        "- **Raster assets** (export frames, panels referenced via Bridge/mediaServe) stay in **Flutter** "
        "`pubspec` asset roots — not in the remote H5 bundle.\n"
        "- Manual deploy gate: upload `h5SiteRoot` → `h5EntryUrlProd`, then switch shell `h5EntryUrl`.\n"
        f"- LaunchScreen placeholder: `{cfg['launchPlaceholderAsset']}` ({cfg['launchPlaceholderSize']}); "
        "real launch art is **out of scope** for this pipeline.\n"
    )
