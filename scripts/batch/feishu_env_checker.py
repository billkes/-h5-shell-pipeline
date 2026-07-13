"""Feishu / lark-cli environment check (trimmed from HaiNaBaiChuan/core/env_checker.py)."""

from __future__ import annotations

import os
import platform
from typing import Any

from batch.feishu_client import (
    get_lark_cli_version,
    install_lark_cli,
    is_lark_cli_installed,
    parse_version,
    run_lark_cmd,
    run_lark_interactive,
)
from batch.feishu_config import get_required_cli_version, get_required_scopes


def _ask_user(prompt: str) -> bool:
    try:
        answer = input(f"  {prompt} (y/n): ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def _scope_strings(config: dict[str, Any]) -> list[str]:
    return [item["scope"] for item in get_required_scopes(config)]


def run_check(config: dict[str, Any]) -> bool:
    print()
    print("═" * 50)
    print("  飞书连接检测 (cursor-ios-batch)")
    print("═" * 50)
    print()

    if not _check_install(config):
        return False
    if not _check_config():
        return False
    if not _check_login(config):
        return False
    if not _check_scopes(config):
        return False

    print()
    _show_summary(config)
    print()
    return True


def _check_install(config: dict[str, Any]) -> bool:
    required_ver = get_required_cli_version(config)

    if not is_lark_cli_installed():
        print("[1/4] lark-cli 未安装 ✗")
        print()
        print("  lark-cli 是飞书官方 CLI，读取主题库 Bitable 需要它。")
        if required_ver:
            print(f"  团队锁定版本: {required_ver}")
        print()

        if not _ask_user("是否由脚本自动安装？"):
            pkg = f"@larksuite/cli@{required_ver}" if required_ver else "@larksuite/cli"
            print()
            print("  请手动执行后重新运行：")
            print(f"  npm install -g {pkg}")
            print()
            return False

        print()
        if not install_lark_cli(required_ver):
            pkg = f"@larksuite/cli@{required_ver}" if required_ver else "@larksuite/cli"
            print(f"  安装失败，请手动: npm install -g {pkg}")
            return False
        if not is_lark_cli_installed():
            print("  安装后仍未检测到 lark-cli")
            return False

    current_ver_str = get_lark_cli_version() or ""
    current_ver = parse_version(current_ver_str)

    if not required_ver:
        print(f"[1/4] lark-cli 已安装 ✓  ({current_ver_str})")
        return True

    required_tuple = parse_version(required_ver)
    if not required_tuple:
        print(f"[1/4] lark-cli 已安装 ✓  ({current_ver_str})")
        return True

    if current_ver == required_tuple:
        print(f"[1/4] lark-cli 已安装 ✓  ({current_ver_str}，版本匹配)")
        return True

    print(f"[1/4] lark-cli 版本不匹配 ✗")
    print(f"  当前: {current_ver_str or '未知'}  期望: {required_ver}")
    print()

    if not _ask_user(f"是否自动切换到 {required_ver}？"):
        print()
        print(f"  npm install -g @larksuite/cli@{required_ver}")
        print()
        return False

    print()
    if not install_lark_cli(required_ver):
        return False

    verify_str = get_lark_cli_version() or ""
    if parse_version(verify_str) == required_tuple:
        print(f"[1/4] lark-cli 版本已对齐 ✓  ({verify_str})")
        return True

    print(f"  切换后版本仍不匹配: {verify_str}")
    return False


def _check_config() -> bool:
    """App credentials live in local lark-cli config — not in this repo."""
    result = run_lark_cmd(["config", "show"])
    app_id = result.get("appId", "")

    if app_id:
        print(f"[2/4] 应用凭证已配置 ✓  ({app_id})")
        return True

    print("[2/4] 应用凭证未配置 ✗")
    print()
    print("  请在本机执行（secret 勿写入 git）：")
    print("  lark-cli config init --app-id <APP_ID> --app-secret-stdin")
    print()
    print("  若已在海纳百川等工具配置过 lark-cli，通常无需重复。")
    print()
    return False


def _check_login(config: dict[str, Any]) -> bool:
    result = run_lark_cmd(["auth", "status"])

    if result.get("ok") is False or "error" in result:
        return _prompt_login("尚未登录飞书", config)

    user_info = result.get("identities", {}).get("user", {})
    token_status = user_info.get("tokenStatus", "")
    user_name = user_info.get("userName", "")
    expires = user_info.get("expiresAt", "")

    if token_status == "valid":
        expires_short = expires[:16] if expires else ""
        print(f"[3/4] 已登录 ✓  ({user_name}，有效期至 {expires_short})")
        return True

    if token_status == "needs_refresh" and user_info.get("refreshExpiresAt"):
        print(f"[3/4] Access Token 过期，尝试静默续期... ({user_name})")
        run_lark_cmd(["config", "show"], timeout=15)
        verify = run_lark_cmd(["auth", "status"])
        verify_user = verify.get("identities", {}).get("user", {})
        if verify_user.get("tokenStatus") == "valid":
            new_expires = verify_user.get("expiresAt", "")[:16]
            print(f"      静默续期成功 ✓  (有效期至 {new_expires})")
            return True
        print("      静默续期失败，需要重新登录")

    return _prompt_login(f"登录已过期 (状态: {token_status})", config)


def _prompt_login(reason: str, config: dict[str, Any]) -> bool:
    print(f"[3/4] {reason} ✗")
    print()
    _show_credential_diagnostics()
    print("  需要登录飞书以读取主题库（只读 scope）。")
    print()

    scope_str = " ".join(_scope_strings(config))

    if not _ask_user("是否现在登录？"):
        print()
        print(f'  lark-cli auth login --scope "{scope_str}"')
        print()
        return False

    print()
    print("  请在浏览器中完成授权...")
    print()
    success = run_lark_interactive(["auth", "login", "--scope", scope_str])

    if success:
        verify = run_lark_cmd(["auth", "status"])
        user = verify.get("identities", {}).get("user", {}).get("userName", "")
        print(f"  登录成功 ✓ ({user})")
        return True

    print(f'  登录未完成，请手动: lark-cli auth login --scope "{scope_str}"')
    return False


def _show_credential_diagnostics() -> None:
    if platform.system() == "Darwin":
        cred_dir = os.path.expanduser("~/Library/Application Support/lark-cli")
    else:
        cred_dir = os.path.expanduser("~/.config/lark-cli")

    if not os.path.isdir(cred_dir):
        print(f"  凭据目录不存在: {cred_dir}")
        print("  首次登录成功后 lark-cli 会在此保存加密凭据。")
        print()


def _check_scopes(config: dict[str, Any]) -> bool:
    result = run_lark_cmd(["auth", "status"])
    user_info = result.get("identities", {}).get("user", {})
    granted_str = user_info.get("scope", "")
    granted_set = set(granted_str.split()) if granted_str else set()

    required = get_required_scopes(config)
    missing: list[str] = []
    results: list[tuple[str, str, bool]] = []

    for item in required:
        scope = item["scope"]
        desc = item["desc"]
        ok = scope in granted_set
        results.append((scope, desc, ok))
        if not ok:
            missing.append(scope)

    total = len(required)
    passed = total - len(missing)

    if not missing:
        print(f"[4/4] 权限检查通过 ✓  ({passed}/{total})")
        return True

    print(f"[4/4] 权限检查未通过 ({passed}/{total})")
    print()
    for i, (scope, desc, ok) in enumerate(results, 1):
        mark = "✓" if ok else "✗"
        print(f"  {i:>2}. [{mark}] {scope:<28} {desc}")
    print()
    print(f"  缺少 {len(missing)} 项权限。")
    print()

    if not _ask_user("是否由脚本自动补充授权？"):
        scope_str = " ".join(missing)
        print()
        print(f'  lark-cli auth login --scope "{scope_str}"')
        print()
        return False

    print()
    print("  请在浏览器中完成授权...")
    print()
    success = run_lark_interactive(["auth", "login", "--scope", " ".join(missing)])

    if success:
        verify = run_lark_cmd(["auth", "status"])
        new_granted = set(
            verify.get("identities", {}).get("user", {}).get("scope", "").split()
        )
        still_missing = [s for s in missing if s not in new_granted]
        if not still_missing:
            print(f"  权限补充完成 ✓ ({total}/{total})")
            return True
        print(f"  仍缺少: {', '.join(still_missing)}")
        return False

    print("  授权未完成")
    return False


def _show_summary(config: dict[str, Any]) -> None:
    version = get_lark_cli_version() or "未知"
    required_ver = get_required_cli_version(config)
    status = run_lark_cmd(["auth", "status"])
    user_info = status.get("identities", {}).get("user", {})
    user = user_info.get("userName", "未知")
    app_id = status.get("appId", "未知")
    scopes = len(get_required_scopes(config))

    ver_display = version
    if required_ver:
        ver_display = f"{version} (锁定: {required_ver})"

    print("  飞书连接检测全部通过")
    print()
    print(f"  lark-cli     {ver_display}  ✓")
    print(f"  应用配置     {app_id}  ✓")
    print(f"  登录状态     {user}  ✓")
    print(f"  权限检查     {scopes}/{scopes}  ✓")
