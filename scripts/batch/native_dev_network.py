"""Native shell LAN dev network: ATS, shellReady fallback, entitlements."""

from __future__ import annotations

import plistlib
import re
from pathlib import Path

from batch.h5_site_paths import H5_PROD_HOST, detect_lan_ip

_ATS_LAN_DOMAIN_KEYS = ("127.0.0.1", "localhost")


def _iter_app_info_plists(workspace: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(workspace.rglob("Info.plist")):
        rel = str(path)
        if "/build/" in rel or "/Pods/" in rel or "/DerivedData/" in rel:
            continue
        if path.parent.name.endswith(".app"):
            continue
        out.append(path)
    return out


def _iter_entitlements(workspace: Path) -> list[Path]:
    return [
        p
        for p in sorted(workspace.glob("*.entitlements"))
        if p.is_file()
    ]


def sync_native_ats_lan_ip(workspace: Path, lan_ip: str | None = None) -> list[str]:
    """Ensure Info.plist ATS allows LAN HTTP (NSAllowsLocalNetworking + current IP)."""
    ip = (lan_ip or detect_lan_ip() or "").strip()
    changed: list[str] = []
    for plist_path in _iter_app_info_plists(workspace):
        try:
            data = plistlib.loads(plist_path.read_bytes())
        except (OSError, plistlib.InvalidFileException):
            continue
        if not isinstance(data, dict):
            continue
        ats = data.setdefault("NSAppTransportSecurity", {})
        if not isinstance(ats, dict):
            ats = {}
            data["NSAppTransportSecurity"] = ats
        before = plistlib.dumps(data)
        ats["NSAllowsLocalNetworking"] = True
        domains = ats.setdefault("NSExceptionDomains", {})
        if not isinstance(domains, dict):
            domains = {}
            ats["NSExceptionDomains"] = domains
        for key in _ATS_LAN_DOMAIN_KEYS:
            domains[key] = {
                "NSExceptionAllowsInsecureHTTPLoads": True,
                "NSIncludesSubdomains": True,
            }
        if ip:
            domains[ip] = {
                "NSExceptionAllowsInsecureHTTPLoads": True,
                "NSIncludesSubdomains": True,
            }
        after = plistlib.dumps(data)
        if after != before:
            plist_path.write_bytes(after)
            changed.append(str(plist_path.resolve().relative_to(workspace.resolve())))
    return changed


def collect_native_dev_network_violations(workspace: Path) -> list[str]:
    """Gate Swift/OC shells for LAN Vite dev reliability."""
    ws = workspace.resolve()
    issues: list[str] = []

    plists = _iter_app_info_plists(ws)
    if not plists:
        issues.append("缺少 ios Info.plist（ATS 无法检测）")
    else:
        ok_ats = False
        for plist_path in plists:
            try:
                data = plistlib.loads(plist_path.read_bytes())
            except (OSError, plistlib.InvalidFileException):
                continue
            ats = data.get("NSAppTransportSecurity") if isinstance(data, dict) else None
            if isinstance(ats, dict) and ats.get("NSAllowsLocalNetworking") is True:
                ok_ats = True
                break
        if not ok_ats:
            issues.append("Info.plist 缺 NSAppTransportSecurity → NSAllowsLocalNetworking（局域网 Vite HTTP）")

    shell_vm = next((p for p in ws.rglob("*WebShellViewModel.swift") if "/build/" not in str(p)), None)
    if shell_vm and shell_vm.is_file():
        text = shell_vm.read_text(encoding="utf-8", errors="ignore")
        if "scheduleShellReadyFallback" not in text:
            issues.append("WebShellViewModel 缺 shellReady fallback（Vite 冷启动易 Load timeout）")
    elif list(ws.rglob("*HostController.m")):
        pass  # OC host — separate path

    web_vc = next((p for p in ws.rglob("*WebViewController.swift") if "/build/" not in str(p)), None)
    if web_vc and web_vc.is_file():
        text = web_vc.read_text(encoding="utf-8", errors="ignore")
        if "scaleToFill" in text and "LaunchPlaceholder" in text:
            issues.append("Launch Veil 使用 scaleToFill — 应改为 scaleAspectFill")

    entitlements = _iter_entitlements(ws)
    if entitlements:
        ok_domains = False
        for ent_path in entitlements:
            try:
                data = plistlib.loads(ent_path.read_bytes())
            except (OSError, plistlib.InvalidFileException):
                continue
            domains = data.get("com.apple.developer.associated-domains") if isinstance(data, dict) else None
            if isinstance(domains, list) and domains:
                ok_domains = True
                break
        if not ok_domains:
            issues.append(
                f"{entitlements[0].name} Associated Domains 为空 — 须含 webcredentials/applinks:{H5_PROD_HOST} 与 webcredentials:localhost"
            )

    project_yml = ws / "project.yml"
    if project_yml.is_file():
        yml = project_yml.read_text(encoding="utf-8", errors="ignore")
        if "CODE_SIGN_ENTITLEMENTS" not in yml and entitlements:
            issues.append("project.yml 未设置 CODE_SIGN_ENTITLEMENTS")

    return issues
