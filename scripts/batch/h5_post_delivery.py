"""Post-delivery fix/audit for H5 shell workspaces (loading + placeholders + IAP policy)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from batch.h5_shell_placeholders import (
    apply_shell_placeholders,
    collect_placeholder_violations,
    prefix_from_workspace,
)
from batch.h5_site_paths import sync_h5_dev_entry_urls
from batch.native_iap_policy import collect_storekit_violations, enforce_no_storekit


def _read_registration(workspace: Path) -> dict:
    for name in ("本包登记信息.json", "register.json"):
        path = workspace / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return {}


def _sync_register_json(workspace: Path, reg: dict) -> bool:
    """Mirror h5 entry URLs from 本包登记信息.json into native register.json when present."""
    target = workspace / "register.json"
    if not target.is_file() or not reg:
        return False
    try:
        native = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if not isinstance(native, dict):
        return False
    keys = (
        "h5EntryUrl",
        "h5EntryUrlDev",
        "h5EntryUrlProd",
        "h5SiteRoot",
        "h5SiteUploadRoot",
        "launchPlaceholderAsset",
    )
    changed = False
    for key in keys:
        if key in reg and native.get(key) != reg[key]:
            native[key] = reg[key]
            changed = True
    if changed:
        target.write_text(json.dumps(native, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def collect_loading_violations(workspace: Path) -> list[str]:
    ws = workspace.resolve()
    issues: list[str] = []
    reg = _read_registration(ws)

    for key in ("h5EntryUrl", "h5EntryUrlProd"):
        if not str(reg.get(key) or "").strip():
            issues.append(f"登记信息缺少 {key}")

    h5_src = ws / "h5" / "src"
    if h5_src.is_dir():
        h5_text = "\n".join(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in h5_src.rglob("*")
            if p.is_file() and p.suffix in {".ts", ".vue", ".js"}
        )
        if re.search(r"setTimeout\s*\(\s*boot", h5_text):
            issues.append("H5 含 setTimeout(boot) — 违反启动时序")
        if "shellReady" not in h5_text:
            issues.append("H5 源码未调用 shellReady")
    else:
        issues.append("缺少 h5/src")

    h5_site = ws / "h5_site"
    slug = str(reg.get("appSlug") or "").strip()
    if slug:
        entry = h5_site / slug / "index.html"
        if not entry.is_file():
            entry = h5_site / "index.html"
        if not entry.is_file():
            issues.append("缺少 h5_site 部署入口（先 npm run build:deploy）")

    native_sources = [
        p
        for suffix in (".m", ".mm", ".swift")
        for p in ws.rglob(f"*{suffix}")
        if "/build/" not in str(p)
        and (
            "HostController" in p.name
            or "WebView" in p.name
            or "WebShell" in p.name
            or "web_view" in p.name.lower()
            or "shell_view" in p.name.lower()
            or "bridge" in p.name.lower()
        )
    ]
    if not native_sources:
        native_sources = [
            p
            for suffix in (".m", ".mm", ".swift")
            for p in ws.rglob(f"*{suffix}")
            if "/build/" not in str(p)
        ][:12]

    joined = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore") for p in native_sources[:20] if p.is_file()
    )
    if joined and "shellReady" not in joined and "WKWebView" in joined:
        issues.append("Native 壳未处理 shellReady 回调")

    if joined and "launch_placeholder" not in joined and "LaunchVeil" not in joined:
        issues.append("Native 壳缺少 launch_placeholder / LaunchVeil 续接")

    return issues


def run_post_delivery(workspace: Path, *, fix: bool, sync_dev_url: bool) -> tuple[list[str], list[str]]:
    ws = workspace.resolve()
    fixes: list[str] = []
    issues: list[str] = []

    if fix:
        for rel in enforce_no_storekit(ws):
            fixes.append(f"移除 StoreKit 本地配置: {rel}")
        try:
            from batch.native_shell_obfuscation import apply_native_shell_obfuscation

            for rel in apply_native_shell_obfuscation(ws):
                fixes.append(rel)
        except OSError:
            pass
        except (ValueError, FileNotFoundError):
            pass
        try:
            from batch.csv_naming import repair_naming_rule_meta_ledgers

            for msg in repair_naming_rule_meta_ledgers(ws):
                fixes.append(msg)
        except OSError:
            pass
        for rel in apply_shell_placeholders(ws, force=True):
            fixes.append(f"写入占位图: {rel}")
        try:
            from batch.h5_layout_contract import sync_h5_layout_contract

            if sync_h5_layout_contract(ws, write=True):
                fixes.append("同步 LAYOUT:pipeline 顶栏/page-shell 契约 → h5/src/styles/global.css")
        except OSError:
            pass
        reg = _read_registration(ws)
        if _sync_register_json(ws, reg):
            fixes.append("同步 register.json ← 本包登记信息.json")

    if sync_dev_url:
        dev = sync_h5_dev_entry_urls(ws, force=True)
        if dev:
            fixes.append(f"刷新硬编码 h5EntryUrl + ATS LAN: {dev}")
        try:
            from batch.native_dev_network import sync_native_ats_lan_ip

            for rel in sync_native_ats_lan_ip(ws):
                fixes.append(f"同步 ATS 局域网例外: {rel}")
        except ImportError:
            pass
    else:
        issues.extend(collect_storekit_violations(ws))

    issues.extend(collect_placeholder_violations(ws))
    issues.extend(collect_loading_violations(ws))
    try:
        from batch.native_dev_network import collect_native_dev_network_violations

        issues.extend(collect_native_dev_network_violations(ws))
    except ImportError:
        pass
    try:
        from batch.native_shell_naming import collect_native_shell_naming_violations

        issues.extend(collect_native_shell_naming_violations(ws))
    except OSError:
        pass
    try:
        from batch.h5_default_seed import collect_h5_default_seed_violations

        issues.extend(collect_h5_default_seed_violations(ws))
    except OSError:
        pass
    try:
        from batch.h5_layout_contract import verify_h5_layout_contract

        issues.extend(verify_h5_layout_contract(ws))
    except OSError:
        pass
    try:
        from batch.h5_visual_lock_gate import collect_h5_visual_lock_violations

        app_name = str(_read_registration(ws).get("appName") or ws.name.split("-")[0] or "").strip()
        issues.extend(collect_h5_visual_lock_violations(ws, app_name))
    except OSError:
        pass
    return fixes, issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="H5 壳产后处理：占位 AppIcon/Launch、加载链路、StoreKit 策略",
    )
    parser.add_argument(
        "workspace",
        type=Path,
        help="产包工作区，如 output/Temioo-OC/Temioo",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="写入占位图、清理 storekit、同步 dev URL / register.json",
    )
    parser.add_argument(
        "--sync-dev-url",
        action="store_true",
        help="刷新 Native 硬编码 Vite LAN 地址 + Info.plist ATS（无需 --fix；勿覆盖编组 A 真图）",
    )
    args = parser.parse_args(argv)

    ws = args.workspace.expanduser().resolve()
    if not ws.is_dir():
        print(f"错误: 工作区不存在: {ws}", file=sys.stderr)
        return 1

    prefix = prefix_from_workspace(ws)
    print(f"工作区: {ws}")
    if prefix:
        print(f"prefix: {prefix}")

    fixes, issues = run_post_delivery(ws, fix=args.fix, sync_dev_url=args.sync_dev_url)

    if fixes:
        print("\n已修复:")
        for line in fixes:
            print(f"  · {line}")

    if issues:
        print("\n待处理:")
        for line in issues:
            print(f"  · {line}")
    else:
        print("\n✅ 产后检查通过")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
