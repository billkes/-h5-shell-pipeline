"""Apply native H5 shell templates into an existing V3 workspace (merge, not wipe)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from batch.csv_tasks import CsvTaskRow
from batch.h5_site_paths import app_slug_from_name
from batch.pack_type import h5_shell_runtime, is_native_ios_runtime
from batch.workspace import dart_prefix


def find_xcode_projects(workspace: Path) -> list[Path]:
    """Return *.xcodeproj / *.xcworkspace under workspace, shallowest first."""
    ws = workspace.resolve()
    found: list[Path] = []
    for pattern in ("*.xcodeproj", "*.xcworkspace"):
        for path in ws.rglob(pattern):
            rel = str(path.relative_to(ws))
            if "/build/" in rel or "DerivedData" in rel:
                continue
            found.append(path)
    found.sort(key=lambda p: len(p.relative_to(ws).parts))
    return found


def has_root_xcode_project(workspace: Path) -> bool:
    ws = workspace.resolve()
    return any(ws.glob("*.xcodeproj")) or any(ws.glob("*.xcworkspace"))


def native_shell_layout_ok(workspace: Path, app_name: str) -> bool:
    """True when xcodeproj sits at workspace root and native sources exist."""
    ws = workspace.resolve()
    if not has_root_xcode_project(ws):
        return False
    runtime = _runtime_from_workspace(ws)
    app_dir = ws / "ios" / app_name if runtime == "swift" else ws / app_name
    if not app_dir.is_dir():
        return False
    suffix = ".swift" if runtime == "swift" else ".m"
    return any(app_dir.rglob(f"*{suffix}"))


def has_launch_screen(workspace: Path, runtime: str) -> bool:
    """OC/Swift 均用 LaunchScreen.storyboard；兼容旧 Swift UILaunchScreen + LaunchBackground。"""
    ws = workspace.resolve()
    if list(ws.rglob("*LaunchScreen*.storyboard")):
        return True
    if runtime != "swift":
        return False
    has_ui_launch = False
    for plist in ws.rglob("Info.plist"):
        if "/build/" in str(plist):
            continue
        try:
            text = plist.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "UILaunchScreen" in text or "UILaunchStoryboardName" in text:
            has_ui_launch = True
            break
    if not has_ui_launch:
        return False
    return any(ws.rglob("**/LaunchBackground.colorset/Contents.json")) or any(
        ws.rglob("**/LaunchPlaceholder.imageset/Contents.json")
    )


def clear_stale_native_shell(workspace: Path, app_name: str) -> list[str]:
    """Remove misplaced xcodeproj / nested native folders before re-apply."""
    ws = workspace.resolve()
    removed: list[str] = []
    for path in find_xcode_projects(ws):
        shutil.rmtree(path, ignore_errors=True)
        removed.append(str(path.relative_to(ws)))
    for folder in (ws / app_name, ws / app_name / app_name):
        if not folder.is_dir() or folder == ws:
            continue
        if any(folder.rglob("*.m")) or any(folder.rglob("*.swift")) or any(
            folder.rglob("*.xcodeproj")
        ):
            shutil.rmtree(folder, ignore_errors=True)
            removed.append(str(folder.relative_to(ws)))
    for name in ("ios", "project.yml", "register.json"):
        target = ws / name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            else:
                target.unlink(missing_ok=True)
            removed.append(name)
    return removed


def _replace_path(src: Path, dest: Path) -> None:
    if dest.exists():
        if dest.is_dir():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def merge_native_shell_staging(staging: Path, workspace: Path, app_name: str, *, runtime: str) -> list[str]:
    """Copy native-only artifacts from a fresh template apply into workspace."""
    merged: list[str] = []
    candidates: tuple[str, ...]
    if runtime == "oc":
        candidates = (f"{app_name}.xcodeproj", app_name, "register.json")
    else:
        candidates = (f"{app_name}.xcodeproj", "ios", "project.yml", "register.json")
    for rel in candidates:
        src = staging / rel
        if not src.exists():
            continue
        dest = workspace / rel
        _replace_path(src, dest)
        merged.append(rel)
    return merged


def _runtime_from_workspace(workspace: Path) -> str:
    reg = workspace / "本包登记信息.json"
    if reg.is_file():
        import json

        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
            runtime = str(data.get("shellRuntime") or "").strip().lower()
            if runtime in ("swift", "oc", "flutter"):
                return runtime
        except json.JSONDecodeError:
            pass
    return "oc"


def _run_apply_script(
    *,
    apply_script: Path,
    template_dir: Path,
    staging: Path,
    app_name: str,
    prefix: str,
    app_slug: str,
    bundle_id: str,
    h5_host: str,
    team_id: str,
    asset_scheme: str,
    provisioning_profile: str,
) -> None:
    cmd = [
        sys.executable,
        str(apply_script),
        "--src",
        str(template_dir),
        "--dst",
        str(staging),
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
        team_id or "",
        "--provisioning-profile",
        provisioning_profile or "",
        "--asset-scheme",
        asset_scheme,
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Native shell apply 失败 (exit {result.returncode}):\n"
            f"{result.stderr or result.stdout}"
        )


def _maybe_xcodegen(staging: Path, app_name: str) -> None:
    import platform

    project_yml = staging / "project.yml"
    if not project_yml.is_file():
        return
    if platform.system() != "Darwin":
        print(f"  >>> xcodegen: 仅 macOS 支持，跳过（{platform.system()}）")
        return
    try:
        result = subprocess.run(
            ["xcodegen", "generate", "--spec", str(project_yml), "--project", str(staging)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "未找到 xcodegen：Swift 壳需在 lock.dimensions 前安装（brew install xcodegen）"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"xcodegen 失败 (exit {result.returncode}):\n{result.stderr or result.stdout}"
        )
    if not any(staging.glob("*.xcodeproj")):
        raise RuntimeError(f"xcodegen 未生成 {app_name}.xcodeproj")


def ensure_native_shell_scaffold(
    *,
    project_dir: Path,
    workspace: Path,
    row: CsvTaskRow,
    bundle_id: str,
    force: bool = False,
) -> list[str]:
    """Idempotently merge oc/swift shell template into an existing V3 workspace."""
    pack_type = row.pack_type or ""
    if not is_native_ios_runtime(pack_type):
        return []

    app_name = row.name
    runtime = h5_shell_runtime(pack_type)
    prefix = dart_prefix(workspace)
    app_slug = app_slug_from_name(app_name)
    h5_host = os.environ.get("H5_PROD_HOST", "")
    team_id = os.environ.get("APPLE_TEAM_ID", "") or os.environ.get("XCODE_DEVELOPMENT_TEAM", "")
    provisioning_profile = os.environ.get("XCODE_PROVISIONING_PROFILE", "duckeggkaifaProfile")
    if not team_id:
        from batch.config import BatchConfig

        team_id = BatchConfig.from_env().xcode_development_team

    if runtime == "oc":
        asset_scheme = f"{prefix}asset"
        template_dir = project_dir / "data" / "static" / "templates" / "oc_shell" / "{{APP_NAME}}"
        apply_script = project_dir / "data" / "static" / "templates" / "oc_shell" / "apply.py"
    elif runtime == "swift":
        asset_scheme = f"{app_slug}-asset"
        template_dir = project_dir / "data" / "static" / "templates" / "swift_shell" / "{{APP_NAME}}"
        apply_script = project_dir / "data" / "static" / "templates" / "swift_shell" / "apply.py"
    else:
        return []

    if not template_dir.is_dir() or not apply_script.is_file():
        raise FileNotFoundError(f"Native shell 模板缺失: {template_dir}")

    needs_apply = force or not native_shell_layout_ok(workspace, app_name)
    if not needs_apply:
        return []

    log: list[str] = []
    if force or find_xcode_projects(workspace):
        for rel in clear_stale_native_shell(workspace, app_name):
            log.append(f"cleared stale native: {rel}")

    with tempfile.TemporaryDirectory(prefix="native-shell-") as tmp:
        staging = Path(tmp) / "staging"
        staging.mkdir()
        _run_apply_script(
            apply_script=apply_script,
            template_dir=template_dir,
            staging=staging,
            app_name=app_name,
            prefix=prefix,
            app_slug=app_slug,
            bundle_id=bundle_id,
            h5_host=h5_host,
            team_id=team_id,
            asset_scheme=asset_scheme,
            provisioning_profile=provisioning_profile,
        )
        if runtime == "swift":
            _maybe_xcodegen(staging, app_name)
        merged = merge_native_shell_staging(staging, workspace, app_name, runtime=runtime)
        log.extend(merged)
        if runtime in ("swift", "oc"):
            from batch.config import BatchConfig
            from batch.xcode_delivery import (
                apply_workspace_ios_signing,
                regenerate_xcodegen_project,
            )

            cfg = BatchConfig.from_env()
            if runtime == "swift":
                regenerate_xcodegen_project(workspace, app_name)
            apply_workspace_ios_signing(cfg, workspace)
        if runtime == "swift":
            from batch.native_shell_naming import (
                apply_native_architecture_folder_rename,
                apply_native_bridge_folder_rename,
            )

            for rel in apply_native_bridge_folder_rename(
                workspace,
                persona=row.programming_style,
                prefix=prefix,
                app_name=app_name,
                runtime=runtime,
            ):
                log.append(rel)
            for rel in apply_native_architecture_folder_rename(
                workspace,
                prefix=prefix,
                app_name=app_name,
                runtime=runtime,
            ):
                log.append(rel)
    return log
