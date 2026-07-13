"""h5_shell remote site paths — URL entry + deployable H5 site root (not Flutter assets)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DEFAULT_H5_SITE_UPLOAD_ROOT = "h5_site/"
DEFAULT_H5_SITE_ROOT = DEFAULT_H5_SITE_UPLOAD_ROOT  # legacy alias
DEFAULT_H5_SOURCE_ROOT = "h5/"
DEFAULT_H5_SITE_ENTRY = "index.html"
H5_PROD_HOST = "test.darin.beauty"
H5_PROD_BASE = f"https://{H5_PROD_HOST}"
H5_VITE_DEV_PORT = 5174
DEFAULT_H5_ENTRY_URL_DEV = f"http://127.0.0.1:{H5_VITE_DEV_PORT}/"
LAUNCH_PLACEHOLDER_SIZE = "1125x2436"
LAUNCH_PLACEHOLDER_ASSET_URI = (
    "native:Assets.xcassets/launch_placeholder.imageset/launch_placeholder.png"
)


def detect_lan_ip() -> str | None:
    """Best-effort LAN IPv4 for cross-device Vite dev / native shell h5EntryUrlDev."""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.25)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return None


def h5_dev_entry_url(*, port: int | None = None) -> str:
    port = port or H5_VITE_DEV_PORT
    ip = detect_lan_ip()
    if ip:
        return f"http://{ip}:{port}/"
    return f"http://127.0.0.1:{port}/"


_LOAD_REGISTER_RE = re.compile(r"- \(void\)\w+LoadRegister \{.*?\n\}", re.DOTALL)
_SWIFT_ENTRY_RE = re.compile(
    r"(static let h5EntryUrl = \")[^\"]+(\";?)",
)


def build_oc_load_register_block(prefix_cap: str, prefix: str, entry_url: str) -> str:
    return (
        f"- (void){prefix_cap}LoadRegister {{\n"
        f"    self.{prefix}EntryUrl = @\"{entry_url}\";\n"
        f"}}"
    )


def sync_native_hardcoded_h5_entry_url(workspace: Path, entry_url: str) -> list[str]:
    """Rewrite OC HostController LoadRegister + Swift ShellConfig to hardcoded Vite URL."""
    ws = workspace.resolve()
    changed: list[str] = []
    for path in sorted(ws.rglob("*HostController.m")):
        if "/build/" in str(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        cap_match = re.search(r"- \(void\)(\w+)LoadRegister", text)
        prop_match = re.search(r"self\.(\w+)EntryUrl =", text)
        if not cap_match or not prop_match:
            continue
        block = build_oc_load_register_block(cap_match.group(1), prop_match.group(1), entry_url)
        new_text, n = _LOAD_REGISTER_RE.subn(block, text, count=1)
        if n and new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed.append(str(path.relative_to(ws)))
    for path in sorted(ws.rglob("*ShellConfig.swift")):
        if "/build/" in str(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        new_text, n = _SWIFT_ENTRY_RE.subn(rf"\1{entry_url}\2", text, count=1)
        if n and new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed.append(str(path.relative_to(ws)))
    return changed


def sync_h5_dev_entry_urls(project: Path, *, port: int | None = None) -> str | None:
    """Refresh h5EntryUrlDev (and loopback h5EntryUrl) in 本包登记信息.json."""
    import json

    reg_path = project / "本包登记信息.json"
    if not reg_path.is_file():
        return None
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(reg, dict):
        return None

    dev_url = h5_dev_entry_url(port=port)
    reg["h5EntryUrlDev"] = dev_url
    entry = str(reg.get("h5EntryUrl") or "")
    if not entry or entry.startswith("http://127.0.0.1") or entry.startswith("http://localhost"):
        reg["h5EntryUrl"] = dev_url
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sync_native_hardcoded_h5_entry_url(project, dev_url)
    return dev_url


def app_slug_from_name(app_name: str) -> str:
    """App display name → URL slug (all lowercase, e.g. Gark → gark)."""
    return re.sub(r"[^a-z0-9]+", "", (app_name or "").strip().lower()) or "app"


def h5_prod_entry_url(app_slug: str, *, entry_name: str = DEFAULT_H5_SITE_ENTRY) -> str:
    """Production WebView URL — directory URL; server serves index.html."""
    slug = (app_slug or "app").strip().lower()
    base = f"{H5_PROD_BASE}/{slug}/"
    if entry_name and entry_name not in ("index.html", "index.htm"):
        return f"{base.rstrip('/')}/{entry_name.lstrip('/')}"
    return base


def site_upload_root_rel() -> str:
    """Workspace upload root containing per-app deploy folders."""
    return DEFAULT_H5_SITE_UPLOAD_ROOT


def site_deploy_dir_rel(reg: dict[str, Any], *, app_name: str = "") -> str:
    """Per-app deploy directory: h5_site/{appSlug}/"""
    slug = str(reg.get("appSlug") or "").strip().lower()
    if not slug and app_name:
        slug = app_slug_from_name(app_name)
    if not slug:
        slug = "app"
    return f"{site_upload_root_rel().rstrip('/')}/{slug}/"


def site_entry_name_from_register(reg: dict[str, Any]) -> str:
    explicit = str(reg.get("h5SiteEntry") or "").strip()
    return explicit or DEFAULT_H5_SITE_ENTRY


def site_entry_rel(reg: dict[str, Any], prefix: str, *, app_name: str = "") -> str:
    explicit = str(reg.get("bundleEntryPath") or reg.get("h5SiteEntryPath") or "").strip()
    if explicit:
        return explicit.replace("\\", "/")
    deploy = site_deploy_dir_rel(reg, app_name=app_name)
    entry_name = site_entry_name_from_register(reg)
    return f"{deploy.rstrip('/')}/{entry_name}"


def resolve_h5_remote_config(
    app_name: str,
    *,
    prefix: str,
    site_root: str | None = None,
    entry_name: str | None = None,
) -> dict[str, Any]:
    """Registration fields for remote-first h5_shell."""
    p = (prefix or "app").strip().lower()
    if not re.fullmatch(r"[a-z]{4,6}", p):
        p = "app"
    slug = app_slug_from_name(app_name)
    deploy_dir = site_deploy_dir_rel({"appSlug": slug})
    if site_root:
        deploy_dir = site_root if site_root.endswith("/") else f"{site_root}/"
    entry = (entry_name or DEFAULT_H5_SITE_ENTRY).strip()
    entry_rel = f"{deploy_dir.rstrip('/')}/{entry}"
    return {
        "appSlug": slug,
        "h5SiteUploadRoot": site_upload_root_rel(),
        "h5SiteRoot": deploy_dir,
        "h5SiteEntry": entry,
        "h5SourceRoot": DEFAULT_H5_SOURCE_ROOT,
        "h5BuildCommand": "npm run build:deploy",
        "h5DevServerPort": str(H5_VITE_DEV_PORT),
        "h5EntryUrlDev": h5_dev_entry_url(),
        "h5EntryUrlProd": h5_prod_entry_url(slug, entry_name=entry),
        "h5EntryUrl": h5_dev_entry_url(),
        "launchPlaceholderAsset": LAUNCH_PLACEHOLDER_ASSET_URI,
        "launchPlaceholderSize": LAUNCH_PLACEHOLDER_SIZE,
        # Legacy keys → per-app deploy dir (not upload root)
        "bundleVaultDir": deploy_dir,
        "bundleEntryPath": entry_rel,
    }


def site_root_from_register(reg: dict[str, Any]) -> str:
    """Per-app deploy directory (h5_site/{appSlug}/)."""
    upload_only = site_upload_root_rel().rstrip("/")
    for key in ("h5SiteRoot", "bundleVaultDir"):
        val = str(reg.get(key) or "").strip().replace("\\", "/")
        if not val:
            continue
        normalized = val if val.endswith("/") else f"{val}/"
        if normalized.rstrip("/") == upload_only:
            return site_deploy_dir_rel(reg)
        return normalized
    return site_deploy_dir_rel(reg)


def site_entry_path(project: Path, reg: dict[str, Any] | None = None) -> Path:
    if reg is None:
        reg = _read_register(project)
    prefix = _resolve_prefix(project, reg)
    app_name = str(reg.get("appName") or "").strip()
    rel = site_entry_rel(reg, prefix, app_name=app_name)
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
        entry = site_entry_name_from_register(reg)
        return h5_prod_entry_url(slug, entry_name=entry)
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
        "- Business H5 is **deployed online** (or Vite dev server during dev); **NOT** bundled in Flutter `pubspec` assets.\n"
        "- **Source tree:** `h5SourceRoot` (`h5/`) — Vue 3 + Vite + vite-plugin-singlefile.\n"
        "- **Deploy layout:** `h5SiteUploadRoot` + `{appSlug}/` + `h5SiteEntry` "
        "(e.g. `h5_site/temioo/index.html`).\n"
        "- **`dev.h5.build`** copies Vite `dist/index.html` → `{bundleEntryPath}`.\n"
        "- Shell WebView loads **hardcoded** native `h5EntryUrl` (Vite LAN during dev; change in `*HostController.m` / `*ShellConfig.swift` before release).\n"
        f"  - appSlug: `{cfg['appSlug']}`\n"
        f"  - h5SiteUploadRoot: `{cfg['h5SiteUploadRoot']}`\n"
        f"  - h5SiteRoot: `{cfg['h5SiteRoot']}` (per-app deploy dir)\n"
        f"  - h5SiteEntry: `{cfg['h5SiteEntry']}`\n"
        f"  - bundleEntryPath: `{cfg['bundleEntryPath']}`\n"
        f"  - h5EntryUrlDev: `{cfg['h5EntryUrlDev']}` (Vite dev — LAN IP + port {cfg['h5DevServerPort']}; run `cd h5 && npm run dev`)\n"
        f"  - h5EntryUrlProd: `{cfg['h5EntryUrlProd']}`\n"
        f"  - h5BuildCommand: `{cfg['h5BuildCommand']}`\n"
        "- **Raster assets** stay in Native `pubspec` / OC assets — not in remote H5 bundle.\n"
        "- Manual deploy: upload `h5_site/{appSlug}/` to CDN path `/{appSlug}/`, set shell `h5EntryUrl` to prod.\n"
        f"- LaunchScreen placeholder: `{cfg['launchPlaceholderAsset']}` ({cfg['launchPlaceholderSize']}).\n"
    )
