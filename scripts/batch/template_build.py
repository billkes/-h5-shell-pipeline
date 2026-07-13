"""End-to-end build pipeline for h5-shell-pipeline.

Reads root ``task.csv`` and produces a buildable workspace under
``output/{app_name}/`` for each package.
"""

from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from batch.config import BatchConfig
from batch.csv_tasks import CsvTaskRow, load_csv_tasks
from batch.h5_bundle_gate import verify_h5_bundle_soft
from batch.h5_deflavor_audit import verify_h5_deflavor_baseline
from batch.h5_legal_ui import verify_h5_legal_ui
from batch.h5_overlay_stack import verify_h5_overlay_stack
from batch.h5_plaza_dev_gate import verify_h5_plaza_dev_gate
from batch.h5_shell_deck import H5_SHELL_BRIDGE_DIM_TO_CSV, draw_h5_shell_to_csv
from batch.h5_site_paths import app_slug_from_name, h5_prod_entry_url, resolve_h5_remote_config
from batch.pack_type import h5_shell_runtime, is_h5_shell, is_native_ios_runtime
from batch.task_schema import (
    COL_BRIDGE_CALLBACK_STYLE,
    COL_BRIDGE_CALL_STYLE,
    COL_BRIDGE_ENVELOPE,
    COL_BRIDGE_ERROR_CODE,
    COL_BRIDGE_INJECT_TIMING,
    COL_MEDIA_SERVE,
    COL_WEBVIEW_ENGINE,
)


@dataclass(frozen=True)
class BuildContext:
    cfg: BatchConfig
    batch_id: str
    output_root: Path
    h5_host: str
    team_id: str


@dataclass(frozen=True)
class BuildResult:
    app_name: str
    pack_type: str
    workspace: Path
    success: bool
    errors: list[str]
    warnings: list[str]


def _derive_prefix(row: CsvTaskRow, app_slug: str) -> str:
    """Derive a 5-letter obfuscation prefix for the shell code."""
    # If naming rule is standard/none, use a short readable prefix.
    rule = (row.naming_obfuscation_rule or "").strip()
    if rule in ("", "无", "标准策略"):
        prefix = re.sub(r"[^a-z]", "", app_slug.lower())[:5]
        return (prefix + "x" * 5)[:5]
    # Otherwise generate a consonant-heavy pseudo-word.
    consonants = "bcdfghjklmnpqrstvwxz"
    vowels = "aeiouy"
    rng = random.Random(row.name + rule)
    pattern = rng.choice(["ccvcc", "cvccv", "ccvcv"])
    out = ""
    for ch in pattern:
        if ch == "c":
            out += rng.choice(consonants)
        else:
            out += rng.choice(vowels)
    return out


def _h5_bridge_selections(row: CsvTaskRow) -> dict[str, str]:
    """Collect drawn bridge dimensions from the row.

    TaskCsv columns use camelCase (e.g. webviewEngine); CsvTaskRow attributes
    are snake_case (e.g. webview_engine).
    """
    attr_map = {
        COL_WEBVIEW_ENGINE: "webview_engine",
        COL_BRIDGE_CALL_STYLE: "bridge_call_style",
        COL_BRIDGE_CALLBACK_STYLE: "bridge_callback_style",
        COL_BRIDGE_ENVELOPE: "bridge_envelope",
        COL_MEDIA_SERVE: "media_serve",
        COL_BRIDGE_ERROR_CODE: "bridge_error_code",
        COL_BRIDGE_INJECT_TIMING: "bridge_inject_timing",
    }
    return {
        dim: getattr(row, attr_map[H5_SHELL_BRIDGE_DIM_TO_CSV[dim]])
        for dim in H5_SHELL_BRIDGE_DIM_TO_CSV
    }


def _write_registration(ctx: BuildContext, row: CsvTaskRow, workspace: Path) -> None:
    app_name = row.name
    app_slug = app_slug_from_name(app_name)
    pack_type = row.pack_type or ctx.cfg.batch_pack_type
    runtime = h5_shell_runtime(pack_type)
    asset_scheme = f"{app_slug}-asset"
    prefix = _derive_prefix(row, app_slug)
    h5_host = ctx.h5_host or os.environ.get("H5_PROD_HOST", "")
    h5_entry_url = h5_prod_entry_url(app_slug) if h5_host else f"https://<H5_PROD_HOST>/{app_slug}/"

    reg: dict[str, Any] = {
        "appName": app_name,
        "appSlug": app_slug,
        "packType": pack_type,
        "shellRuntime": runtime,
        "h5EntryUrl": h5_entry_url,
        "assetScheme": asset_scheme,
        "bridgeDeckSelections": _h5_bridge_selections(row),
        "bridgeCapabilities": [
            "shellReady",
            "getPermissionStatus",
            "requestPermission",
            "pickImage",
            "takePhoto",
            "startRecording",
            "stopRecording",
            "getProducts",
            "purchase",
            "mediaServe",
            "ensureSeedAssets",
            "sendFeedback",
            "shareText",
        ],
    }
    # Merge remote H5 site registration fields (h5SiteRoot/Entry, bundleEntryPath, etc.)
    reg.update(resolve_h5_remote_config(app_name, prefix=prefix))
    # Prefer prod URL once host is known; dev URL remains available for local iteration.
    if h5_host:
        reg["h5EntryUrl"] = reg["h5EntryUrlProd"]
    else:
        reg["h5EntryUrl"] = reg["h5EntryUrlProd"]
    (workspace / "本包登记信息.json").write_text(
        json.dumps(reg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _copy_h5_docs(cfg: BatchConfig, workspace: Path) -> None:
    docs = cfg.docs_dir
    names = [
        "H5-Bridge协议.md",
        "H5壳业务流程文字版.md",
        "H5去风味规范.md",
        "H5壳IAP协议.md",
        "H5壳Swift实现规范.md",
        "H5壳Legal弹层规范.md",
        "H5壳Overlay路由规范.md",
        "H5壳启动闪屏规范.md",
        "H5壳广场页规范.md",
        "H5壳Vault合规维护规范.md",
    ]
    for name in names:
        src = docs / name
        if src.is_file():
            shutil.copy2(src, workspace / name)


def _resolve_h5_dir(workspace: Path) -> Path | None:
    for name in ("h5_site", "h5"):
        candidate = workspace / name
        if candidate.is_dir():
            return candidate
    return None


def _run_h5_gates(workspace: Path, row: CsvTaskRow) -> tuple[list[str], list[str]]:
    """Run H5 quality gates; return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    h5_dir = _resolve_h5_dir(workspace)
    if h5_dir is None:
        warnings.append("h5_site/ 或 h5/ 不存在，跳过 H5 gate")
        return errors, warnings

    try:
        warnings.extend(verify_h5_bundle_soft(workspace, flutter_dir=h5_dir))
    except Exception as exc:
        warnings.append(f"h5_bundle_gate 异常: {exc}")

    try:
        issues = verify_h5_deflavor_baseline(h5_dir)
        errors.extend(issues)
    except Exception as exc:
        warnings.append(f"h5_deflavor_audit 异常: {exc}")

    try:
        issues = verify_h5_legal_ui(h5_dir)
        errors.extend(issues)
    except Exception as exc:
        warnings.append(f"h5_legal_ui 异常: {exc}")

    try:
        issues = verify_h5_overlay_stack(h5_dir)
        errors.extend(issues)
    except Exception as exc:
        warnings.append(f"h5_overlay_stack 异常: {exc}")

    try:
        issues = verify_h5_plaza_dev_gate(h5_dir)
        errors.extend(issues)
    except Exception as exc:
        warnings.append(f"h5_plaza_dev_gate 异常: {exc}")

    return errors, warnings


def _apply_swift_shell_template(ctx: BuildContext, row: CsvTaskRow, workspace: Path) -> None:
    app_name = row.name
    app_slug = app_slug_from_name(app_name)
    prefix = _derive_prefix(row, app_slug)
    h5_host = ctx.h5_host or os.environ.get("H5_PROD_HOST", "")
    # 测试/流水线阶段使用固定测试包名。
    bundle_id = ctx.cfg.xcode_bundle_id
    asset_scheme = f"{app_slug}-asset"

    template_dir = ctx.cfg.project_dir / "data" / "static" / "templates" / "swift_shell" / "{{APP_NAME}}"
    apply_script = (
        ctx.cfg.project_dir / "data" / "static" / "templates" / "swift_shell" / "apply.py"
    )
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Swift shell 模板不存在: {template_dir}")
    if not apply_script.is_file():
        raise FileNotFoundError(f"Swift shell apply 脚本不存在: {apply_script}")

    cmd = [
        sys.executable,
        str(apply_script),
        "--src",
        str(template_dir),
        "--dst",
        str(workspace),
        "--app-name",
        app_name,
        "--prefix",
        prefix,
        "--app-slug",
        app_slug,
        "--h5-host",
        h5_host or "<H5_PROD_HOST>",
        "--bundle-id",
        bundle_id,
        "--team-id",
        ctx.team_id,
        "--asset-scheme",
        asset_scheme,
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Swift shell apply 失败 (exit {result.returncode}):\n"
            f"{result.stderr or result.stdout}"
        )
    print(result.stdout.strip())


def _apply_oc_shell_template(ctx: BuildContext, row: CsvTaskRow, workspace: Path) -> None:
    app_name = row.name
    app_slug = app_slug_from_name(app_name)
    prefix = _derive_prefix(row, app_slug)
    h5_host = ctx.h5_host or os.environ.get("H5_PROD_HOST", "")
    bundle_id = ctx.cfg.xcode_bundle_id
    asset_scheme = f"{prefix}asset"

    template_dir = ctx.cfg.project_dir / "data" / "static" / "templates" / "oc_shell" / "{{APP_NAME}}"
    apply_script = ctx.cfg.project_dir / "data" / "static" / "templates" / "oc_shell" / "apply.py"
    if not template_dir.is_dir():
        raise FileNotFoundError(f"OC shell 模板不存在: {template_dir}")
    if not apply_script.is_file():
        raise FileNotFoundError(f"OC shell apply 脚本不存在: {apply_script}")

    cmd = [
        sys.executable,
        str(apply_script),
        "--src",
        str(template_dir),
        "--dst",
        str(workspace),
        "--app-name",
        app_name,
        "--prefix",
        prefix,
        "--app-slug",
        app_slug,
        "--h5-host",
        h5_host or "<H5_PROD_HOST>",
        "--bundle-id",
        bundle_id,
        "--team-id",
        ctx.team_id or "",
        "--asset-scheme",
        asset_scheme,
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"OC shell apply 失败 (exit {result.returncode}):\n"
            f"{result.stderr or result.stdout}"
        )
    print(result.stdout.strip())


def build_one(ctx: BuildContext, row: CsvTaskRow) -> BuildResult:
    app_name = row.name
    pack_type = row.pack_type or ctx.cfg.batch_pack_type
    workspace = ctx.output_root / app_name
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    errors: list[str] = []
    warnings: list[str] = []

    # Ensure bridge dimensions are present for H5 shells.
    if is_h5_shell(pack_type) and not row.webview_engine:
        warnings.append("Bridge 七维为空，尝试自动抽卡")
        draw_h5_shell_to_csv(ctx.cfg.task_csv, ctx.cfg.project_dir, batch_id=ctx.batch_id)
        # Reload row to get drawn values.
        for r in load_csv_tasks(ctx.cfg.task_csv):
            if r.name == app_name:
                row = r
                break

    # Apply native shell template.
    if is_native_ios_runtime(pack_type):
        if h5_shell_runtime(pack_type) == "swift":
            try:
                _apply_swift_shell_template(ctx, row, workspace)
            except Exception as exc:
                errors.append(f"Swift shell 模板应用失败: {exc}")
        elif h5_shell_runtime(pack_type) == "oc":
            try:
                _apply_oc_shell_template(ctx, row, workspace)
            except Exception as exc:
                errors.append(f"OC shell 模板应用失败: {exc}")
        else:
            errors.append(f"未知 native runtime: {pack_type}")
    elif is_h5_shell(pack_type):
        # Flutter shell template not yet in place; create minimal workspace.
        errors.append("h5_flutter_shell / h5_shell Flutter 模板尚未实现")
    else:
        errors.append(f"未知应用类型: {pack_type}")

    # Always write registration and copy docs if shell applied or attempted.
    if not errors or is_native_ios_runtime(pack_type):
        try:
            _write_registration(ctx, row, workspace)
        except Exception as exc:
            errors.append(f"登记信息生成失败: {exc}")
        try:
            _copy_h5_docs(ctx.cfg, workspace)
        except Exception as exc:
            warnings.append(f"文档拷贝失败: {exc}")

    # Run H5 gates if h5/ exists.
    gate_errors, gate_warnings = _run_h5_gates(workspace, row)
    errors.extend(gate_errors)
    warnings.extend(gate_warnings)

    success = not errors
    return BuildResult(
        app_name=app_name,
        pack_type=pack_type,
        workspace=workspace,
        success=success,
        errors=errors,
        warnings=warnings,
    )


def ensure_h5_bridge_drawn(ctx: BuildContext) -> None:
    """Pre-draw Bridge 七维 for h5 shells before strict validation."""
    pre_rows = load_csv_tasks(
        ctx.cfg.task_csv,
        strict_extended=False,
        project_dir=ctx.cfg.project_dir,
    )
    h5_apps = [
        r.name
        for r in pre_rows
        if is_h5_shell(r.pack_type) and not r.webview_engine
    ]
    if h5_apps:
        draw_h5_shell_to_csv(
            ctx.cfg.task_csv,
            ctx.cfg.project_dir,
            batch_id=ctx.batch_id,
            apps=h5_apps,
        )


def build_all(ctx: BuildContext) -> list[BuildResult]:
    ensure_h5_bridge_drawn(ctx)
    rows = load_csv_tasks(ctx.cfg.task_csv, strict_extended=True, project_dir=ctx.cfg.project_dir)
    if not rows:
        raise ValueError(f"{ctx.cfg.task_csv} 没有有效任务")
    results: list[BuildResult] = []
    for row in rows:
        print(f"\n>>> 开始构建: {row.name} ({row.pack_type or ctx.cfg.batch_pack_type})")
        result = build_one(ctx, row)
        results.append(result)
        status = "✅ 成功" if result.success else "❌ 失败"
        print(f"{status}: {result.app_name}")
        for err in result.errors:
            print(f"   错误: {err}")
        for warn in result.warnings:
            print(f"   警告: {warn}")
    return results


def print_summary(results: list[BuildResult]) -> int:
    total = len(results)
    ok = sum(1 for r in results if r.success)
    print(f"\n{'=' * 60}")
    print(f"构建汇总: {ok}/{total} 成功")
    print(f"{'=' * 60}")
    for r in results:
        mark = "✅" if r.success else "❌"
        print(f"{mark} {r.app_name:<20} {r.pack_type:<18} {r.workspace}")
    return 0 if ok == total else 1


def cmd_build_cli(argv: list[str]) -> int:
    """CLI entry: ``build <name>`` or ``build-all``."""
    from batch.legacy_cli import main as legacy_main

    if not argv:
        print("用法: build <应用主名称> | build-all")
        return 1
    if argv[0] == "all" or argv[0] == "build-all":
        return legacy_main(["build-all", *argv[1:]])
    return legacy_main(["build", argv[0], *argv[1:]])
