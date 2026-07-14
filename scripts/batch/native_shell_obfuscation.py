"""Apply transform_identifier naming to native Swift/OC shell scaffold."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from batch.h5_shell_placeholders import prefix_from_workspace
from batch.naming import NamingMeta, meta_from_lock, transform_identifier
from batch.native_shell_naming import native_app_dir, _resolve_app_name
from batch.pack_type import h5_shell_runtime

REGISTER_FILE = "本包登记信息.json"
COMBO_FILE = "本包代码组合.json"

# Semantic keys → (entity, legacy basename patterns with {app} placeholder).
_NATIVE_SYMBOLS: list[tuple[str, str, str]] = [
    ("bridge_shell", "folder", "Bridge"),
    ("seed_bundle", "folder", "SeedBundle"),
    ("photos_seed", "folder", "photos/seed"),
    ("web_bridge_handler", "file", "WebBridgeHandler.swift"),
    ("file_vault", "file", "{app}FileVault.swift"),
    ("seed_assets", "file", "{app}SeedAssets.swift"),
    ("asset_scheme", "file", "{app}AssetScheme.swift"),
    ("shell_config", "file", "{app}ShellConfig.swift"),
    ("webview_deflavor", "file", "{app}WebViewDeflavor.swift"),
    ("iap_manager", "file", "IAPManager.swift"),
    ("image_picker", "file", "ImagePickerCoordinator.swift"),
    ("permission_manager", "file", "PermissionManager.swift"),
    ("audio_recorder", "file", "AudioRecorderManager.swift"),
    ("feedback_mail", "file", "FeedbackMailComposer.swift"),
    ("top_most_vc", "file", "UIViewController+TopMost.swift"),
    ("web_content_resolver", "file", "WebContentResolver.swift"),
    ("web_content_source", "file", "WebContentSource.swift"),
    ("web_shell_view_model", "file", "WebShellViewModel.swift"),
    ("web_view_controller", "file", "WebViewController.swift"),
    ("web_shell_viewing", "file", "WebShellViewing.swift"),
    ("app_entry", "file", "{app}App.swift"),
    ("web_bridge_handler", "class", "WebBridgeHandler"),
    ("file_vault", "class", "{app}FileVault"),
    ("bundle_media", "class", "{app}BundleMedia"),
    ("seed_assets", "class", "{app}SeedAssets"),
    ("asset_scheme", "class", "{app}AssetScheme"),
    ("shell_config", "class", "{app}ShellConfig"),
    ("webview_deflavor", "class", "{app}WebViewDeflavor"),
    ("iap_manager", "class", "IAPManager"),
    ("image_picker", "class", "ImagePickerCoordinator"),
    ("permission_manager", "class", "PermissionManager"),
    ("audio_recorder", "class", "AudioRecorderManager"),
    ("feedback_mail", "class", "FeedbackMailComposer"),
    ("web_content_resolver", "class", "WebContentResolver"),
    ("web_content_source", "class", "WebContentSource"),
    ("web_shell_view_model", "class", "{app}WebShellViewModel"),
    ("web_view_controller", "class", "{app}WebViewController"),
    ("web_shell_viewing", "protocol", "WebShellViewing"),
    ("launch_style", "class", "{app}LaunchStyle"),
    ("host_container", "class", "{app}HostContainer"),
    ("app_entry", "class", "{app}App"),
    ("audio_result", "class", "AudioResult"),
    ("top_most", "local", "{app_lower}TopMost"),
    ("ensure_copied", "method", "ensureCopied"),
    ("attach_view", "method", "attachView"),
    ("handle_shell_ready", "method", "handleShellReady"),
    ("request_load", "method", "requestLoad"),
    ("apply_deflavor", "method", "apply"),
    ("install_deflavor", "method", "install"),
    ("asset_scheme_field", "field", "assetScheme"),
    ("h5_entry_url", "field", "h5EntryUrl"),
    ("seed_filenames", "field", "seedFilenames"),
]

_SEMANTIC_DIR_NAMES = frozenset({"Bridge", "SeedBundle", "Modules", "WebContent", "WebView"})
_SEMANTIC_FILE_STEMS = frozenset(
    {
        "WebBridgeHandler",
        "WebContentResolver",
        "WebContentSource",
        "WebShellViewModel",
        "WebViewController",
        "WebShellViewing",
        "PermissionManager",
        "ImagePickerCoordinator",
        "AudioRecorderManager",
        "IAPManager",
        "FeedbackMailComposer",
    }
)

__all__ = [
    "apply_native_shell_obfuscation",
    "build_native_obfuscation_map",
    "collect_native_semantic_violations",
    "expected_native_seed_bundle_dir",
    "expected_native_shell_dir",
]


@dataclass(frozen=True)
class NativeObfuscationMap:
    meta: NamingMeta
    replacements: dict[str, str]
    shell_dir: str
    seed_bundle_dir: str
    photos_seed_path: str
    file_renames: dict[str, str]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _load_meta(workspace: Path) -> NamingMeta:
    ws = workspace.resolve()
    for name in (COMBO_FILE, REGISTER_FILE, "本包维度锁.json"):
        data = _read_json(ws / name)
        if data:
            try:
                return meta_from_lock(data)
            except (ValueError, KeyError):
                continue
    raise ValueError(f"{ws}: 无法读取 namingRuleMeta v2")


def _t(meta: NamingMeta, entity: str, semantic: str) -> str:
    return transform_identifier(
        rule_key=meta.rule_key,
        meta=meta,
        entity=entity,  # type: ignore[arg-type]
        semantic=semantic,
        salt=semantic,
    )


def build_native_obfuscation_map(workspace: Path, *, app_name: str = "") -> NativeObfuscationMap:
    ws = workspace.resolve()
    app = (app_name or _resolve_app_name(ws)).strip()
    app_lower = app[:1].lower() + app[1:] if app else "app"
    meta = _load_meta(ws)

    replacements: dict[str, str] = {}
    file_renames: dict[str, str] = {}

    for semantic, entity, legacy in _NATIVE_SYMBOLS:
        old = legacy.format(app=app, app_lower=app_lower)
        new = _t(meta, entity, semantic)
        if old == new:
            continue
        if entity == "file":
            file_renames[old] = new
        else:
            replacements[old] = new

    deflavor = replacements.get(f"{app}WebViewDeflavor", f"{app}WebViewDeflavor")
    apply_new = _t(meta, "method", "apply_deflavor")
    install_new = _t(meta, "method", "install_deflavor")
    replacements[f"{deflavor}.apply"] = f"{deflavor}.{apply_new}"
    replacements[f"{deflavor}.install"] = f"{deflavor}.{install_new}"
    if "apply" in replacements:
        del replacements["apply"]
    if "install" in replacements:
        del replacements["install"]

    return NativeObfuscationMap(
        meta=meta,
        replacements=replacements,
        shell_dir=_t(meta, "folder", "bridge_shell"),
        seed_bundle_dir=_t(meta, "folder", "seed_bundle"),
        photos_seed_path=_t(meta, "folder", "photos_seed"),
        file_renames=file_renames,
    )


def expected_native_shell_dir(workspace: Path) -> str:
    return build_native_obfuscation_map(workspace).shell_dir


def expected_native_seed_bundle_dir(workspace: Path) -> str:
    return build_native_obfuscation_map(workspace).seed_bundle_dir


def collect_native_semantic_violations(workspace: Path) -> list[str]:
    """Strict gate: no semantic Bridge/SeedBundle or scaffold symbol names."""
    ws = workspace.resolve()
    reg = _read_json(ws / REGISTER_FILE)
    if not reg:
        return []
    pack_type = str(reg.get("packType") or "")
    runtime = h5_shell_runtime(pack_type) if pack_type else str(reg.get("shellRuntime") or "")
    if runtime != "swift":
        return []

    app_name = str(reg.get("appName") or _resolve_app_name(ws)).strip()
    app_dir = native_app_dir(ws, app_name=app_name, runtime=runtime)
    if app_dir is None:
        return ["缺少 ios/{AppName}/ Native 源码目录"]

    try:
        obf = build_native_obfuscation_map(ws, app_name=app_name)
    except ValueError as exc:
        return [str(exc)]

    issues: list[str] = []

    if (app_dir / "Bridge").is_dir():
        issues.append(
            f"禁止语义目录 Bridge/ — 须为 `{obf.shell_dir}/`（transform_identifier）"
        )
    if (app_dir / "SeedBundle").is_dir():
        issues.append(
            f"禁止语义目录 SeedBundle/ — 须为 `{obf.seed_bundle_dir}/`"
        )
    if not (app_dir / obf.shell_dir).is_dir() and not (app_dir / "Bridge").is_dir():
        issues.append(f"缺少 Native shell 目录 `{obf.shell_dir}/`")

    for bad in _SEMANTIC_DIR_NAMES:
        if bad in {"Bridge", "SeedBundle"}:
            continue
        if (app_dir / bad).is_dir():
            issues.append(f"禁止语义目录 `{bad}/`")

    for swift in sorted(app_dir.rglob("*.swift")):
        stem = swift.stem.split("+", 1)[0]
        if stem in _SEMANTIC_FILE_STEMS or (
            stem.startswith(app_name) and stem not in {f"{app_name}App"}
        ):
            if any(stem == s.format(app=app_name, app_lower=app_name[:1].lower() + app_name[1:]).split(".")[0]
                   for _, _, s in _NATIVE_SYMBOLS if s.endswith(".swift")):
                rel = swift.relative_to(ws)
                if stem in _SEMANTIC_FILE_STEMS or re.match(
                    rf"^{re.escape(app_name)}(FileVault|SeedAssets|AssetScheme|ShellConfig|WebViewDeflavor|WebShellViewModel|WebViewController|LaunchStyle|HostContainer)$",
                    stem,
                ):
                    issues.append(f"Swift 文件名仍含语义/品牌名: `{rel}`")

        text = swift.read_text(encoding="utf-8", errors="ignore")
        for old in obf.replacements:
            if "." in old:
                continue
            if len(old) < 4:
                continue
            if re.search(rf"\b{re.escape(old)}\b", text):
                rel = swift.relative_to(ws)
                issues.append(f"Swift 符号 `{old}` 未混淆: `{rel}`")
                break

    for swift in sorted(app_dir.rglob("*.swift")):
        if "SeedBundle" in swift.read_text(encoding="utf-8", errors="ignore"):
            issues.append(f"字符串仍引用 SeedBundle: `{swift.relative_to(ws)}`")
            break

    if any("photos/seed" in p.read_text(encoding="utf-8", errors="ignore")
           for p in ws.rglob("*") if p.is_file() and p.suffix in {".swift", ".ts", ".tsx"}):
        issues.append(
            f"Documents seed 路径仍用 photos/seed — 须为 `{obf.photos_seed_path}`"
        )

    return issues


def _apply_replacements(text: str, replacements: dict[str, str]) -> str:
    ordered = sorted(replacements.items(), key=lambda kv: len(kv[0]), reverse=True)
    out = text
    for old, new in ordered:
        out = re.sub(rf"\b{re.escape(old)}\b", new, out)
    return out


def _patch_project_yml(ws: Path, seed_bundle_dir: str) -> None:
    yml = ws / "project.yml"
    if not yml.is_file():
        return
    text = yml.read_text(encoding="utf-8")
    text = re.sub(
        r"path:\s*ios/\{\{APP_NAME\}\}/SeedBundle",
        f"path: ios/{{{{APP_NAME}}}}/{seed_bundle_dir}",
        text,
    )
    text = text.replace("/SeedBundle", f"/{seed_bundle_dir}")
    yml.write_text(text, encoding="utf-8")


def _patch_h5_seed_prefix(ws: Path, photos_seed_path: str) -> None:
    for rel in (
        "h5/src/lib/vaultAsset.ts",
        "h5/src/lib/pickImage.ts",
    ):
        path = ws / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        text = text.replace("photos/seed/", f"{photos_seed_path}/")
        text = text.replace("SeedBundle", expected_native_seed_bundle_dir(ws))
        path.write_text(text, encoding="utf-8")


def _persist_obfuscation_paths(ws: Path, obf: NativeObfuscationMap) -> None:
    reg_path = ws / REGISTER_FILE
    reg = _read_json(reg_path) or {}
    cac = reg.setdefault("codeAntiCorrelation", {})
    if not isinstance(cac, dict):
        cac = {}
        reg["codeAntiCorrelation"] = cac
    cac["nativeShellDir"] = obf.shell_dir
    cac["nativeSeedBundleDir"] = obf.seed_bundle_dir
    cac["photosSeedPath"] = obf.photos_seed_path
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_native_shell_obfuscation(workspace: Path, *, app_name: str = "") -> list[str]:
    """Rename shell dirs/files/symbols to transform_identifier names."""
    ws = workspace.resolve()
    app = (app_name or _resolve_app_name(ws)).strip()
    app_dir = native_app_dir(ws, app_name=app, runtime="swift")
    if app_dir is None:
        raise FileNotFoundError(f"ios/{app}/ not found")

    obf = build_native_obfuscation_map(ws, app_name=app)
    changed: list[str] = []

    # 1) Rewrite Swift sources in place (before file renames).
    for swift in sorted(app_dir.rglob("*.swift")):
        original = swift.read_text(encoding="utf-8")
        updated = _apply_replacements(original, obf.replacements)
        updated = updated.replace("SeedBundle", obf.seed_bundle_dir)
        updated = updated.replace("photos/seed/", f"{obf.photos_seed_path}/")
        if updated != original:
            swift.write_text(updated, encoding="utf-8")
            changed.append(f"rewrite: {swift.relative_to(ws)}")

    # 2) Rename Swift files.
    for old_name, new_name in sorted(obf.file_renames.items(), key=lambda kv: len(kv[0]), reverse=True):
        for path in list(app_dir.rglob(old_name)):
            dest = path.with_name(new_name)
            if path != dest:
                path.rename(dest)
                changed.append(f"file: {path.relative_to(ws)} → {dest.name}")

    # 3) Rename Bridge / SeedBundle directories.
    bridge = app_dir / "Bridge"
    shell = app_dir / obf.shell_dir
    if bridge.is_dir() and not shell.is_dir():
        bridge.rename(shell)
        changed.append(f"dir: Bridge/ → {obf.shell_dir}/")
    seed = app_dir / "SeedBundle"
    seed_dest = app_dir / obf.seed_bundle_dir
    if seed.is_dir() and not seed_dest.is_dir():
        seed.rename(seed_dest)
        changed.append(f"dir: SeedBundle/ → {obf.seed_bundle_dir}/")

    _patch_project_yml(ws, obf.seed_bundle_dir)
    _patch_h5_seed_prefix(ws, obf.photos_seed_path)
    _persist_obfuscation_paths(ws, obf)
    return changed
