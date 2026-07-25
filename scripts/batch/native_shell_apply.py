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
    # Swift: ios/{app}; OC: {app}/ — detect by tree (登记信息 may not exist yet).
    swift_dir = ws / "ios" / app_name
    if swift_dir.is_dir() and any(swift_dir.rglob("*.swift")):
        return True
    oc_dir = ws / app_name
    return oc_dir.is_dir() and any(oc_dir.rglob("*.m"))


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
    import json

    reg = workspace / "本包登记信息.json"
    if reg.is_file():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
            runtime = str(data.get("shellRuntime") or "").strip().lower()
            if runtime in ("swift", "oc", "flutter"):
                return runtime
        except json.JSONDecodeError:
            pass
    state = workspace / ".build-state.json"
    if state.is_file():
        try:
            data = json.loads(state.read_text(encoding="utf-8"))
            pack_type = str(data.get("pack_type") or "").strip().lower()
            if "swift" in pack_type:
                return "swift"
            if "oc" in pack_type:
                return "oc"
            if "flutter" in pack_type:
                return "flutter"
        except json.JSONDecodeError:
            pass
    if (workspace / "ios").is_dir():
        return "swift"
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
    """Best-effort xcodegen on macOS. Never required when skeleton already provided .xcodeproj."""
    import platform

    project_yml = staging / "project.yml"
    if not project_yml.is_file():
        return
    if (staging / f"{app_name}.xcodeproj" / "project.pbxproj").is_file():
        print("  >>> xcodegen: 已有 .xcodeproj，跳过")
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
    except FileNotFoundError:
        print("  >>> xcodegen: 未安装，跳过（依赖 ios_app_skeleton 的 .xcodeproj）")
        return
    if result.returncode != 0:
        print(
            f"  >>> xcodegen 失败，保留已有骨架 .xcodeproj:\n"
            f"{result.stderr or result.stdout}"
        )
        return
    if not any(staging.glob("*.xcodeproj")):
        print(f"  >>> xcodegen 未生成 {app_name}.xcodeproj，依赖骨架回退")


def _run_ios_app_skeleton_apply(
    *,
    project_dir: Path,
    staging: Path,
    app_name: str,
    bundle_id: str,
    team_id: str,
) -> None:
    apply_script = project_dir / "data" / "static" / "templates" / "ios_app_skeleton" / "apply.py"
    template_dir = (
        project_dir / "data" / "static" / "templates" / "ios_app_skeleton" / "{{APP_NAME}}"
    )
    if not apply_script.is_file() or not template_dir.is_dir():
        raise FileNotFoundError(
            f"ios_app_skeleton 缺失: {template_dir}（Swift 壳在 Windows 上需要官方骨架提供 .xcodeproj）"
        )
    cmd = [
        sys.executable,
        str(apply_script),
        "--src",
        str(template_dir),
        "--dst",
        str(staging),
        "--app-name",
        app_name,
        "--bundle-id",
        bundle_id,
        "--team-id",
        team_id or "",
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ios_app_skeleton apply 失败 (exit {result.returncode}):\n"
            f"{result.stderr or result.stdout}"
        )
    pbx = staging / f"{app_name}.xcodeproj" / "project.pbxproj"
    if not pbx.is_file():
        raise RuntimeError(f"ios_app_skeleton 未产出 project.pbxproj: {pbx}")


def _strip_pbxproj_file(text: str, filename: str) -> str:
    """Remove lines that reference a missing source file (e.g. ContentView.swift)."""
    return "".join(
        line for line in text.splitlines(keepends=True) if filename not in line
    )


def _retarget_skeleton_pbxproj_to_ios(pbxproj: Path, app_name: str, ios_app_dir: Path) -> None:
    """Point Apple skeleton sources group at ios/{app}; drop missing ContentView."""
    text = pbxproj.read_text(encoding="utf-8")
    # Source group path = AppName → ios/AppName (avoid renaming AppName.app product).
    text = text.replace(
        f"\t\t\tpath = {app_name};\n\t\t\tsourceTree = \"<group>\";",
        f"\t\t\tpath = ios/{app_name};\n\t\t\tsourceTree = \"<group>\";",
    )
    if not (ios_app_dir / "ContentView.swift").is_file():
        text = _strip_pbxproj_file(text, "ContentView.swift")
    pbxproj.write_text(text, encoding="utf-8")


def _compose_swift_staging(
    *,
    skeleton_staging: Path,
    shell_staging: Path,
    out_staging: Path,
    app_name: str,
) -> list[str]:
    """Merge official skeleton .xcodeproj + swift_shell ios/ into one staging root."""
    log: list[str] = []
    out_staging.mkdir(parents=True, exist_ok=True)

    for rel in ("ios", "project.yml", f"{app_name}.entitlements", "register.json"):
        src = shell_staging / rel
        if src.exists():
            _replace_path(src, out_staging / rel)
            log.append(f"shell:{rel}")

    shell_proj = shell_staging / f"{app_name}.xcodeproj"
    skel_proj = skeleton_staging / f"{app_name}.xcodeproj"
    out_proj = out_staging / f"{app_name}.xcodeproj"

    if shell_proj.is_dir() and (shell_proj / "project.pbxproj").is_file():
        _replace_path(shell_proj, out_proj)
        log.append(f"shell:{app_name}.xcodeproj")
    elif skel_proj.is_dir() and (skel_proj / "project.pbxproj").is_file():
        _replace_path(skel_proj, out_proj)
        ios_app = out_staging / "ios" / app_name
        _retarget_skeleton_pbxproj_to_ios(out_proj / "project.pbxproj", app_name, ios_app)
        log.append(f"skeleton:{app_name}.xcodeproj (retarget → ios/{app_name})")
    else:
        raise RuntimeError(
            "Swift 壳缺少 .xcodeproj：需要 macOS xcodegen 或 data/static/templates/ios_app_skeleton"
        )

    if not (out_staging / "ios" / app_name).is_dir():
        raise RuntimeError(f"swift_shell 未产出 ios/{app_name}/")
    return log


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

        if runtime == "swift":
            skel_staging = Path(tmp) / "skeleton"
            shell_staging = Path(tmp) / "shell"
            skel_staging.mkdir()
            shell_staging.mkdir()
            _run_ios_app_skeleton_apply(
                project_dir=project_dir,
                staging=skel_staging,
                app_name=app_name,
                bundle_id=bundle_id,
                team_id=team_id,
            )
            log.append("applied: ios_app_skeleton")
            _run_apply_script(
                apply_script=apply_script,
                template_dir=template_dir,
                staging=shell_staging,
                app_name=app_name,
                prefix=prefix,
                app_slug=app_slug,
                bundle_id=bundle_id,
                h5_host=h5_host,
                team_id=team_id,
                asset_scheme=asset_scheme,
                provisioning_profile=provisioning_profile,
            )
            log.append("applied: swift_shell")
            # macOS: optional full project from project.yml; Windows: skeleton .xcodeproj.
            _maybe_xcodegen(shell_staging, app_name)
            compose_log = _compose_swift_staging(
                skeleton_staging=skel_staging,
                shell_staging=shell_staging,
                out_staging=staging,
                app_name=app_name,
            )
            log.extend(compose_log)
        else:
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
                # macOS: full regen from project.yml; Windows: keep skeleton pbxproj.
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
