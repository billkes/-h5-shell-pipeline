"""Native iOS shell directory naming — Bridge folder vs obfuscated {prefix}_shell."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from batch.architecture_folders import architecture_folders_from_lock, semantic_dir_pattern
from batch.csv_tasks import CsvTaskRow, normalize_programming_style
from batch.h5_shell_placeholders import prefix_from_workspace
from batch.pack_type import h5_shell_runtime
from batch.programming_layout import (
    H5_VAULT_PATTERN_BY_ASSET_LAYOUT,
    persona_key,
    resolve_persona_layout,
)

# 标准英文 persona 保留语义化 Bridge/；其余 persona 须用 {prefix}_shell/。
STANDARD_BRIDGE_PERSONAS = frozenset({"美国人", "英国人", "中国人"})

FORBIDDEN_SEMANTIC_NATIVE_DIRS = frozenset(
    {"Bridge", "Modules", "WebContent", "WebView"}
)

__all__ = [
    "STANDARD_BRIDGE_PERSONAS",
    "apply_native_bridge_folder_rename",
    "build_native_shell_naming_prompt_block",
    "collect_native_shell_naming_violations",
    "collect_programming_style_sources",
    "native_bridge_folder_basename",
    "uses_semantic_bridge_dir",
]


def uses_semantic_bridge_dir(persona: str) -> bool:
    return persona_key(persona) in STANDARD_BRIDGE_PERSONAS


def native_bridge_folder_basename(persona: str, prefix: str) -> str:
    if uses_semantic_bridge_dir(persona):
        return "Bridge"
    p = (prefix or "").strip().lower()
    if not re.fullmatch(r"[a-z]{4,6}", p):
        return "Bridge"
    return f"{p}_shell"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _style_from_payload(data: dict[str, Any]) -> str:
    ps = data.get("programmingStyle")
    if isinstance(ps, str) and ps.strip():
        return normalize_programming_style(ps) or ps.strip()
    if isinstance(ps, dict):
        val = str(ps.get("value") or "").strip()
        if val:
            return normalize_programming_style(val) or val
    cac = data.get("codeAntiCorrelation")
    if isinstance(cac, dict):
        val = str(cac.get("programmingStyle") or "").strip()
        if val:
            return normalize_programming_style(val) or val
    return ""


def collect_programming_style_sources(workspace: Path) -> dict[str, str]:
    """Return programmingStyle values found in each workspace ledger file."""
    ws = workspace.resolve()
    sources: dict[str, str] = {}
    for label, name in (
        ("本包登记信息.json", "本包登记信息.json"),
        ("本包代码组合.json", "本包代码组合.json"),
        ("本包维度锁.json", "本包维度锁.json"),
        ("本包资源布局.json", "本包资源布局.json"),
    ):
        data = _read_json(ws / name)
        if not data:
            continue
        style = _style_from_payload(data)
        if style:
            sources[label] = style
    return sources


def _read_programming_style(workspace: Path) -> str:
    sources = collect_programming_style_sources(workspace)
    if sources:
        return next(iter(sources.values()))
    return ""


def _collect_programming_style_violations(
    ws: Path,
    reg: dict[str, Any],
    *,
    persona: str,
    prefix: str,
    app_dir: Path | None,
    runtime: str,
) -> list[str]:
    issues: list[str] = []
    sources = collect_programming_style_sources(ws)

    if not persona:
        issues.append("缺少编程风格 programmingStyle（本包登记信息.json / 本包代码组合.json）")
        return issues

    unique = set(sources.values())
    if len(unique) > 1:
        detail = "；".join(f"{k}={v}" for k, v in sorted(sources.items()))
        issues.append(f"编程风格台账不一致：{detail}")

    expected_layout = resolve_persona_layout(persona, prefix=prefix)
    expected_lib = str(expected_layout.get("libLayout") or "")
    expected_asset = str(expected_layout.get("assetLayout") or "")
    expected_vault = H5_VAULT_PATTERN_BY_ASSET_LAYOUT.get(expected_asset, "")

    reg_lib = str(reg.get("libLayout") or "").strip()
    reg_asset = str(reg.get("h5VaultLayout") or reg.get("assetLayout") or "").strip()
    reg_vault = str(reg.get("h5VaultPattern") or "").strip()

    lock = _read_json(ws / "本包维度锁.json") or {}
    ps_lock = lock.get("programmingStyle")
    if isinstance(ps_lock, dict):
        lock_lib = str(ps_lock.get("libLayout") or "").strip()
        lock_asset = str(ps_lock.get("assetLayout") or "").strip()
        if lock_lib and expected_lib and lock_lib != expected_lib:
            issues.append(
                f"编程风格 {persona} 要求 libLayout=`{expected_lib}`，"
                f"本包维度锁.json 为 `{lock_lib}`"
            )
        if lock_asset and expected_asset and lock_asset != expected_asset:
            issues.append(
                f"编程风格 {persona} 要求 assetLayout=`{expected_asset}`，"
                f"本包维度锁.json 为 `{lock_asset}`"
            )

    resource = _read_json(ws / "本包资源布局.json") or {}
    res_lib = str(resource.get("libLayout") or "").strip()
    res_asset = str(resource.get("assetLayout") or "").strip()
    if res_lib and expected_lib and res_lib != expected_lib:
        issues.append(
            f"编程风格 {persona} 要求 libLayout=`{expected_lib}`，"
            f"本包资源布局.json 为 `{res_lib}`"
        )
    if res_asset and expected_asset and res_asset != expected_asset:
        issues.append(
            f"编程风格 {persona} 要求 assetLayout=`{expected_asset}`，"
            f"本包资源布局.json 为 `{res_asset}`"
        )

    if reg_asset and expected_asset and reg_asset != expected_asset:
        issues.append(
            f"编程风格 {persona} 要求 h5VaultLayout/assetLayout=`{expected_asset}`，"
            f"本包登记信息.json 为 `{reg_asset}`"
        )
    if reg_vault and expected_vault and reg_vault != expected_vault:
        issues.append(
            f"编程风格 {persona} 要求 h5VaultPattern=`{expected_vault}`，"
            f"本包登记信息.json 为 `{reg_vault}`"
        )

    if uses_semantic_bridge_dir(persona) and prefix:
        shell_dir = f"{prefix}_shell"
        if app_dir and runtime == "swift" and (app_dir / shell_dir).is_dir():
            issues.append(
                f"标准编程风格 {persona} 应使用 `Bridge/`，禁止混淆目录 `{shell_dir}/`"
            )

    return issues


def _collect_architecture_folder_violations(
    ws: Path,
    app_dir: Path,
    *,
    prefix: str,
) -> list[str]:
    issues: list[str] = []
    combo = _read_json(ws / "本包代码组合.json") or {}
    reg = _read_json(ws / "本包登记信息.json") or {}
    cac = reg.get("codeAntiCorrelation")
    lock_payload: dict[str, Any] = dict(combo)
    if isinstance(cac, dict):
        lock_payload.setdefault("architectureFolders", cac.get("architectureFolders"))
        lock_payload.setdefault("namingObfuscationRule", {
            "dartCodePrefix": cac.get("dartCodePrefix") or prefix,
        })
    folders = architecture_folders_from_lock(lock_payload)
    if not folders:
        return issues

    expected_names = {
        str(entry.get("folderBasename") or "").strip()
        for entry in folders.values()
        if isinstance(entry, dict)
    }
    expected_names.discard("")

    on_disk = {
        child.name
        for child in app_dir.iterdir()
        if child.is_dir()
        and child.name.startswith(f"{prefix}_")
        and child.name != f"{prefix}_shell"
    }

    for name in sorted(expected_names):
        if not (app_dir / name).is_dir():
            issues.append(
                f"架构 role 目录缺失 `{name}/` — 须对齐 architectureFolders 锁定名"
            )

    stale = on_disk - expected_names
    for name in sorted(stale):
        issues.append(
            f"Native 壳存在未锁定架构目录 `{name}/` — "
            "须使用 architectureFolders.folderBasename"
        )

    return issues


def _resolve_app_name(workspace: Path) -> str:
    for name in ("本包登记信息.json", "register.json"):
        path = workspace / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            app = str(data.get("appName") or "").strip()
            if app:
                return app
    return workspace.name


def native_app_dir(workspace: Path, *, app_name: str = "", runtime: str = "") -> Path | None:
    ws = workspace.resolve()
    app = (app_name or _resolve_app_name(ws)).strip()
    if not app:
        return None
    rt = (runtime or "").strip().lower()
    if not rt:
        reg_path = ws / "本包登记信息.json"
        if reg_path.is_file():
            try:
                reg = json.loads(reg_path.read_text(encoding="utf-8"))
                rt = str(reg.get("shellRuntime") or "").strip().lower()
            except json.JSONDecodeError:
                rt = ""
        if not rt:
            rt = "swift"
    if rt == "swift":
        candidate = ws / "ios" / app
        return candidate if candidate.is_dir() else None
    candidate = ws / app
    return candidate if candidate.is_dir() else None


def collect_native_shell_naming_violations(workspace: Path) -> list[str]:
    """Flag Bridge/persona/layout naming issues for native H5 shells."""
    ws = workspace.resolve()
    reg_path = ws / "本包登记信息.json"
    if not reg_path.is_file():
        return []

    reg = _read_json(reg_path)
    if reg is None:
        return ["本包登记信息.json JSON 无效"]

    pack_type = str(reg.get("packType") or "")
    runtime = h5_shell_runtime(pack_type) if pack_type else str(reg.get("shellRuntime") or "")
    if runtime not in {"swift", "oc"}:
        return []

    persona = _read_programming_style(ws)
    prefix = prefix_from_workspace(ws)
    app_name = str(reg.get("appName") or _resolve_app_name(ws)).strip()
    app_dir = native_app_dir(ws, app_name=app_name, runtime=runtime)

    issues: list[str] = []
    issues.extend(
        _collect_programming_style_violations(
            ws,
            reg,
            persona=persona,
            prefix=prefix,
            app_dir=app_dir,
            runtime=runtime,
        )
    )

    if app_dir is None:
        return issues

    expected = native_bridge_folder_basename(persona, prefix)

    if runtime == "swift":
        for bad in sorted(FORBIDDEN_SEMANTIC_NATIVE_DIRS):
            if (app_dir / bad).is_dir() and bad != expected:
                issues.append(
                    f"Native 壳禁止语义目录 `{bad}/`（编程风格={persona or '未知'}；"
                    f"应使用 `{expected}/`）"
                )
        expected_path = app_dir / expected
        if not uses_semantic_bridge_dir(persona) and not expected_path.is_dir():
            if (app_dir / "Bridge").is_dir():
                issues.append(
                    f"Bridge 目录未遵循命名规则：须重命名为 `{expected}/`"
                )
            else:
                issues.append(f"缺少 Native 桥接目录 `{expected}/`")
        if prefix and not uses_semantic_bridge_dir(persona):
            pat = semantic_dir_pattern(prefix)
            for child in app_dir.iterdir():
                if not child.is_dir():
                    continue
                if pat.match(child.name):
                    issues.append(
                        f"Native 壳存在语义架构目录 `{child.name}/` — "
                        "须使用 本包代码组合.json architectureFolders 锁定名"
                    )
        if prefix:
            issues.extend(
                _collect_architecture_folder_violations(ws, app_dir, prefix=prefix)
            )

    try:
        from batch.csv_naming import collect_naming_rule_meta_violations

        issues.extend(collect_naming_rule_meta_violations(ws))
    except OSError:
        pass

    return issues


def apply_native_bridge_folder_rename(
    workspace: Path,
    *,
    persona: str = "",
    prefix: str = "",
    app_name: str = "",
    runtime: str = "swift",
) -> list[str]:
    """Rename Bridge/ → {prefix}_shell/ for obfuscated personas (idempotent)."""
    ws = workspace.resolve()
    persona = persona or _read_programming_style(ws)
    prefix = (prefix or prefix_from_workspace(ws)).strip()
    app = (app_name or _resolve_app_name(ws)).strip()
    if uses_semantic_bridge_dir(persona):
        return []

    app_dir = native_app_dir(ws, app_name=app, runtime=runtime)
    if app_dir is None:
        return []

    expected = native_bridge_folder_basename(persona, prefix)
    bridge = app_dir / "Bridge"
    target = app_dir / expected
    if bridge.is_dir() and bridge != target:
        if target.exists():
            raise FileExistsError(f"无法重命名 Bridge/：目标已存在 {target}")
        bridge.rename(target)
        rel = target.relative_to(ws).as_posix()
        return [f"重命名 Bridge/ → {rel}"]
    return []


def build_native_shell_naming_prompt_block(
    row: CsvTaskRow | None,
    *,
    prefix: str = "",
) -> str:
    if row is None:
        return ""
    p = (prefix or "").strip().lower()
    folder = native_bridge_folder_basename(row.programming_style, p)
    if uses_semantic_bridge_dir(row.programming_style):
        rule = (
            f"- Native bridge directory MUST be `{folder}/` (standard semantic layout).\n"
            "- Class/file names: PascalCase English (`WebBridgeHandler.swift`).\n"
        )
    else:
        rule = (
            f"- Native bridge directory MUST be `{folder}/` — NEVER `Bridge/`, "
            "`Modules/`, `WebContent/`, `WebView/`.\n"
            "- Apply namingObfuscationRule to Swift files/classes under this folder.\n"
            "- WKScriptMessageHandler channel names stay in 本包登记信息.json / H5 bootstrap.\n"
        )
    expected_layout = resolve_persona_layout(row.programming_style, prefix=p)
    expected_lib = str(expected_layout.get("libLayout") or "")
    expected_asset = str(expected_layout.get("assetLayout") or "")
    expected_vault = H5_VAULT_PATTERN_BY_ASSET_LAYOUT.get(expected_asset, "")
    return (
        "\n[Native Shell Naming — REQUIRED]\n"
        f"- programmingStyle: {row.programming_style}\n"
        f"- libLayout (dim-6): `{expected_lib}`\n"
        f"- assetLayout / h5VaultLayout (dim-7): `{expected_asset}`\n"
        f"- h5VaultPattern: `{expected_vault}`\n"
        f"{rule}"
        "- programmingStyle MUST match across 本包登记信息.json / 本包代码组合.json / "
        "本包维度锁.json.\n"
        "- Architecture role folders: ONLY names from architectureFolders in "
        "本包代码组合.json / 本包维度锁.json.\n"
    )
