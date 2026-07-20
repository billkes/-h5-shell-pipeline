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

# swift_shell 模板 MVP 默认架构目录（lock.dimensions 生成名不同，须对齐）
_SWIFT_SHELL_TEMPLATE_ROLE_DIRS: dict[str, tuple[str, str]] = {
    "models": ("ember_pulse", "ember_pulse_leaf"),
    "entities": ("ember_pulse", "ember_pulse_leaf"),
    "views": ("quill_dock", "quill_dock_leaf"),
    "presenters": ("pulse_mesh", "pulse_mesh_leaf"),
    "controllers": ("pulse_mesh", "pulse_mesh_leaf"),
    "viewmodels": ("pulse_mesh", "pulse_mesh_leaf"),
}
_STUB_ONLY_ARCH_ROLES = frozenset({"interactors", "routers"})

__all__ = [
    "STANDARD_BRIDGE_PERSONAS",
    "apply_native_architecture_folder_rename",
    "apply_native_bridge_folder_rename",
    "build_native_shell_naming_prompt_block",
    "collect_native_shell_naming_violations",
    "collect_programming_style_sources",
    "native_bridge_folder_basename",
    "resolve_native_bridge_folder_basename",
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


def resolve_native_bridge_folder_basename(
    workspace: Path,
    persona: str,
    prefix: str,
) -> str:
    """Prefer persisted nativeShellDir after obfuscation; else {prefix}_shell."""
    ws = workspace.resolve()
    for name in ("本包登记信息.json", "本包代码组合.json"):
        data = _read_json(ws / name)
        if not data:
            continue
        cac = data.get("codeAntiCorrelation")
        if isinstance(cac, dict):
            native_dir = str(cac.get("nativeShellDir") or "").strip()
            if native_dir:
                return native_dir
    return native_bridge_folder_basename(persona, prefix)


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


def apply_native_architecture_folder_rename(
    workspace: Path,
    *,
    prefix: str = "",
    app_name: str = "",
    runtime: str = "swift",
) -> list[str]:
    """Rename swift_shell template role dirs → architectureFolders lock names."""
    ws = workspace.resolve()
    prefix = (prefix or prefix_from_workspace(ws)).strip()
    if not prefix:
        return []

    combo = _read_json(ws / "本包代码组合.json") or {}
    reg = _read_json(ws / "本包登记信息.json") or {}
    cac = reg.get("codeAntiCorrelation")
    lock_payload: dict[str, Any] = dict(combo)
    if isinstance(cac, dict):
        lock_payload.setdefault("architectureFolders", cac.get("architectureFolders"))
    folders = architecture_folders_from_lock(lock_payload)
    if not folders:
        return []

    app = (app_name or _resolve_app_name(ws)).strip()
    app_dir = native_app_dir(ws, app_name=app, runtime=runtime)
    if app_dir is None:
        return []

    changed: list[str] = []
    claimed_templates: set[tuple[str, str]] = set()

    for role, entry in folders.items():
        if not isinstance(entry, dict):
            continue
        locked_folder = str(entry.get("folderBasename") or "").strip()
        locked_leaf = str(entry.get("stubBasename") or "").strip()
        if not locked_folder:
            continue

        tpl = _SWIFT_SHELL_TEMPLATE_ROLE_DIRS.get(role)
        stub_only = role in _STUB_ONLY_ARCH_ROLES or tpl is None
        dest_folder = app_dir / locked_folder

        if tpl and tpl not in claimed_templates:
            folder_suffix, _leaf_suffix = tpl
            src_folder = app_dir / f"{prefix}_{folder_suffix}"
            if src_folder.is_dir() and src_folder != dest_folder:
                if dest_folder.exists():
                    raise FileExistsError(
                        f"无法重命名 `{src_folder.name}/`：目标已存在 `{dest_folder.name}/`"
                    )
                src_folder.rename(dest_folder)
                changed.append(
                    f"dir: {src_folder.relative_to(ws)} → {dest_folder.relative_to(ws)}"
                )
            claimed_templates.add(tpl)
        elif stub_only and not dest_folder.is_dir():
            dest_folder.mkdir(parents=True, exist_ok=True)
            changed.append(f"mkdir: {dest_folder.relative_to(ws)}")

        role_root = dest_folder if dest_folder.is_dir() else None
        if role_root is None and tpl and tpl in claimed_templates:
            folder_suffix, _ = tpl
            fallback = app_dir / f"{prefix}_{folder_suffix}"
            if fallback.is_dir():
                role_root = fallback
        if role_root is None or not locked_leaf:
            continue

        dest_leaf = role_root / locked_leaf
        if tpl:
            _folder_suffix, leaf_suffix = tpl
            src_leaf = role_root / f"{prefix}_{leaf_suffix}"
            if src_leaf.is_dir() and src_leaf != dest_leaf:
                if dest_leaf.exists():
                    raise FileExistsError(
                        f"无法重命名 `{src_leaf.name}/`：目标已存在 `{dest_leaf.name}/`"
                    )
                src_leaf.rename(dest_leaf)
                changed.append(
                    f"dir: {src_leaf.relative_to(ws)} → {dest_leaf.relative_to(ws)}"
                )
        elif stub_only:
            dest_leaf.mkdir(parents=True, exist_ok=True)
            if not any(dest_leaf.glob("*.swift")):
                anchor = locked_leaf.replace(f"{prefix}_", "").replace("_anchor", "")
                stub_name = f"{prefix}_{anchor}_stub.swift"
                (dest_leaf / stub_name).write_text(
                    "// Pipeline VIPER architecture anchor stub\nimport Foundation\n",
                    encoding="utf-8",
                )
                changed.append(f"stub: {dest_leaf.relative_to(ws)}/{stub_name}")
    return changed


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


_NATIVE_BRIDGE_CHANNEL_RE = re.compile(r'name:\s*@?"([A-Za-z0-9_]*Bridge)"')
_NATIVE_BRIDGE_CALLBACK_RE = re.compile(r"window\.([A-Za-z0-9_]+BridgeCallback)\b")
_H5_BRIDGE_CHANNEL_TOKEN_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*Bridge)\b")
_H5_SRC_SUFFIXES = frozenset({".ts", ".tsx", ".js", ".mjs", ".vue"})
_NATIVE_BRIDGE_SUFFIXES = frozenset({".swift", ".m", ".mm"})


def _collect_bridge_channel_violations(ws: Path, app_dir: Path | None) -> list[str]:
    """Native ↔ H5 WKScriptMessageHandler channel/callback names must match.

    Native registers window.webkit.messageHandlers.<appLower>Bridge and replies via
    window.<appLower>BridgeCallback. When the agent-authored H5 posts to a different
    channel (e.g. derived from the code prefix), the shell never receives the message
    and every bridge call silently falls back to the H5 stub — IAP / device / file all
    break with no error. See 《H5-Bridge协议.md》 §5 通道命名 (LOCKED).
    """
    if app_dir is None or not app_dir.is_dir():
        return []

    native_channels: set[str] = set()
    native_callbacks: set[str] = set()
    for path in app_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _NATIVE_BRIDGE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        native_channels.update(_NATIVE_BRIDGE_CHANNEL_RE.findall(text))
        native_callbacks.update(_NATIVE_BRIDGE_CALLBACK_RE.findall(text))
    if not native_channels:
        return []

    h5_src = ws / "h5" / "src"
    if not h5_src.is_dir():
        return []
    parts: list[str] = []
    for path in h5_src.rglob("*"):
        if path.is_file() and path.suffix.lower() in _H5_SRC_SUFFIXES:
            try:
                parts.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    h5_text = "\n".join(parts)
    if not h5_text.strip():
        return []

    issues: list[str] = []
    if not any(channel in h5_text for channel in native_channels):
        h5_channels = sorted(set(_H5_BRIDGE_CHANNEL_TOKEN_RE.findall(h5_text)))
        issues.append(
            "Native ↔ H5 桥通道名不一致：native 注册 "
            f"{sorted(native_channels)}，但 h5/src 未引用（H5 用了 {h5_channels or '无'}）。"
            "WKWebView 仅注册 native 通道名，名字对不上则 bridge 调用静默走 H5 stub"
            "（IAP/设备/存图失效且无报错）。H5 通道名须由 App 名派生并与 native 一致"
            "（见《H5-Bridge协议.md》§5）。"
        )
    if native_callbacks and not any(cb in h5_text for cb in native_callbacks):
        issues.append(
            "Native ↔ H5 桥回调名不一致：native 回调 "
            f"{sorted(native_callbacks)}，h5/src 未定义该全局函数，Promise 永不 resolve"
            "（见《H5-Bridge协议.md》§5）。"
        )
    return issues


def collect_native_shell_naming_violations(
    workspace: Path,
    *,
    strict_semantic: bool = False,
) -> list[str]:
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

    issues.extend(_collect_bridge_channel_violations(ws, app_dir))

    expected = resolve_native_bridge_folder_basename(ws, persona, prefix)

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

    try:
        from batch.native_shell_obfuscation import collect_native_semantic_violations

        reg_data = _read_json(ws / "本包登记信息.json") or {}
        cac = reg_data.get("codeAntiCorrelation")
        native_dir = (
            str(cac.get("nativeShellDir") or "").strip()
            if isinstance(cac, dict)
            else ""
        )
        if strict_semantic or native_dir:
            issues.extend(collect_native_semantic_violations(ws))
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
        f"- libLayout (dim-6, Flutter/H5 vault topology — not native code shape): `{expected_lib}`\n"
        f"- assetLayout / h5VaultLayout (dim-7, H5 deploy — not native code shape): `{expected_asset}`\n"
        f"- h5VaultPattern: `{expected_vault}`\n"
        f"{rule}"
        "- Native Swift/OC **implementation** style: 编程人设风格.md dims 2–5.\n"
        "- programmingStyle MUST match across 本包登记信息.json / 本包代码组合.json / "
        "本包维度锁.json.\n"
        "- Architecture role folders: ONLY names from architectureFolders in "
        "本包代码组合.json / 本包维度锁.json.\n"
    )
