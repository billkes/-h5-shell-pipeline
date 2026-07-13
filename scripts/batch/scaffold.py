"""Deterministic Flutter package scaffold from dimension lock."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from batch.architecture_folders import (
    architecture_folders_from_lock,
    resolve_all_role_folder_basenames,
    semantic_dir_pattern,
    stub_class_name,
)
from batch.dimension_lock import (
    resolve_dimension_lock,
    update_scaffold_files,
)
from batch.flutter_ops import find_flutter_project
from batch.programming_layout import (
    layout_from_lock,
    refresh_tool_asset_manifest,
    role_implementation_subdir,
    skin_bucket_name,
    write_resource_layout_manifest,
)
from batch.scaffold_templates import (
    PATTERN_FORBIDDEN_DIRS,
    PATTERN_ROLE_DIRS,
    PATTERN_ROLE_STUBS,
    STATE_DEPENDENCIES,
    STATE_DEV_DEPENDENCIES,
    expected_scaffold_paths,
    generate_app_dart,
    generate_global_background,
    generate_home_placeholder,
    generate_image_box,
    generate_main_dart,
    generate_palette_tokens,
    generate_role_stub,
    lib_root_segment,
    prefix_pascal,
)


def _merge_yaml_section(
    text: str,
    section: str,
    new_deps: dict[str, str],
) -> str:
    if not new_deps:
        return text
    pattern = re.compile(
        rf"^{section}:\s*\n((?:  .+\n)*)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    existing: dict[str, str] = {}
    if match:
        block = match.group(1)
        for line in block.splitlines():
            m = re.match(r"^\s{2}(\w+):\s*(.+)$", line)
            if m:
                existing[m.group(1)] = m.group(2).strip()
    merged = {**existing, **new_deps}
    lines = [f"{section}:"]
    for name in sorted(merged):
        lines.append(f"  {name}: {merged[name]}")
    replacement = "\n".join(lines) + "\n"
    if match:
        return text[: match.start()] + replacement + text[match.end() :]
    if not text.endswith("\n"):
        text += "\n"
    return text + replacement


def merge_pubspec_dependencies(
    pubspec_path: Path,
    state_key: str,
    *,
    include_features: bool = True,
) -> None:
    from batch.scaffold_templates import FEATURE_DEPENDENCIES

    text = pubspec_path.read_text(encoding="utf-8")
    deps: dict[str, str] = {}
    if include_features:
        deps.update(FEATURE_DEPENDENCIES)
    deps.update(STATE_DEPENDENCIES.get(state_key, {}))
    dev_deps = STATE_DEV_DEPENDENCIES.get(state_key, {})
    text = _merge_yaml_section(text, "dependencies", deps)
    text = _merge_yaml_section(text, "dev_dependencies", dev_deps)
    pubspec_path.write_text(text, encoding="utf-8")


def _state_key(lock: dict[str, Any]) -> str:
    sm = lock.get("stateManagement") or {}
    return str(sm.get("key") or "").strip().lower()


def _pattern_key(lock: dict[str, Any]) -> str:
    ap = lock.get("architecturePattern") or {}
    return str(ap.get("key") or "").strip().lower()


def _prefix(lock: dict[str, Any]) -> str:
    naming = lock.get("namingObfuscationRule") or {}
    return str(naming.get("dartCodePrefix") or "").strip()


def _dart_pkg(lock: dict[str, Any], fallback: str) -> str:
    pkg = str(lock.get("dartPackageName") or "").strip()
    return pkg or fallback


def _views_folder_basename(lock: dict[str, Any], prefix: str, pattern_key: str) -> str:
    folders = architecture_folders_from_lock(lock)
    if "views" in folders:
        return folders["views"].get("folderBasename", f"{prefix}_views")
    mapping = resolve_all_role_folder_basenames(lock, prefix, pattern_key)
    return mapping.get("views", f"{prefix}_views")


def _write_stub(
    path: Path,
    *,
    role: str,
    prefix: str,
    entry: dict[str, str],
    pattern_key: str,
) -> None:
    if role == "models":
        pascal = prefix_pascal(prefix)
        content = f"""/// Obfuscated model-layer anchor for {pascal}.
abstract class {pascal}ShapeCore {{
  // region: business-impl
  // endregion
}}
"""
    elif role in PATTERN_ROLE_STUBS.get(pattern_key, {}):
        suffix = PATTERN_ROLE_STUBS[pattern_key][role]
        class_name = stub_class_name(prefix, entry) if entry else f"{prefix_pascal(prefix)}Base{suffix}"
        content = generate_role_stub(prefix, role, suffix).replace(
            f"{prefix_pascal(prefix)}Base{suffix}",
            class_name,
        )
    else:
        content = ""
    if content:
        path.write_text(content, encoding="utf-8")


_DUAL_HUB_CORE_ROLES = frozenset({"models", "entities"})


def _write_skin_files(
    bucket_dir: Path,
    *,
    prefix: str,
    seg: str,
    bucket_name: str,
    written: list[str],
) -> None:
    bucket_dir.mkdir(parents=True, exist_ok=True)
    skin_files = {
        f"{prefix}_palette_tokens.dart": generate_palette_tokens(prefix),
        f"{prefix}_global_background.dart": generate_global_background(prefix),
        f"{prefix}_image_box.dart": generate_image_box(prefix),
    }
    for fname, content in skin_files.items():
        (bucket_dir / fname).write_text(content, encoding="utf-8")
        written.append(f"lib/{seg}/{bucket_name}/{fname}")


def _role_parent(
    lib_root: Path,
    *,
    lib_layout: str,
    prefix: str,
    role: str,
    folder_basename: str,
) -> Path:
    if lib_layout == "dual_hub":
        hub = (
            f"{prefix}_core"
            if role in _DUAL_HUB_CORE_ROLES
            else f"{prefix}_surface"
        )
        return lib_root / hub / folder_basename
    return lib_root / folder_basename


def _ensure_impl_subdir(
    role_dir: Path,
    *,
    prefix: str,
    role: str,
    lib_layout: str,
    written: list[str],
    rel_prefix: str,
) -> None:
    sub = role_implementation_subdir(prefix, role, lib_layout)
    if not sub:
        return
    impl = role_dir / sub
    impl.mkdir(parents=True, exist_ok=True)
    gitkeep = impl / ".gitkeep"
    if not gitkeep.is_file():
        gitkeep.write_text("", encoding="utf-8")
    written.append(f"{rel_prefix}/{sub}/.gitkeep")


def scaffold_flutter_package(
    workspace: Path,
    *,
    dart_package_name: str,
) -> list[str]:
    """Generate dimension-locked skeleton; return relative paths written."""
    lock = resolve_dimension_lock(workspace)
    if lock is None:
        raise ValueError(f"缺少维度锁文件，无法生成脚手架: {workspace}")

    fp = find_flutter_project(workspace) or workspace
    pubspec = fp / "pubspec.yaml"
    if not pubspec.is_file():
        raise FileNotFoundError(f"pubspec.yaml 不存在: {pubspec}")

    prefix = _prefix(lock)
    if not re.fullmatch(r"[a-z]{4,6}", prefix):
        raise ValueError(f"dartCodePrefix 无效: {prefix!r}")

    layout = layout_from_lock(lock)
    lib_layout = str(layout.get("libLayout") or "flat_skin_role")
    skin_bucket = str(
        layout.get("skinBucket") or skin_bucket_name(prefix, lib_layout)
    )

    state_key = _state_key(lock)
    pattern_key = _pattern_key(lock)
    dart_pkg = _dart_pkg(lock, dart_package_name)
    seg = lib_root_segment(prefix, dart_pkg)
    lib_root = fp / "lib" / seg
    written: list[str] = []

    folder_map = architecture_folders_from_lock(lock)
    if not folder_map:
        folder_map = {
            role: {
                "role": role,
                "folderBasename": f"{prefix}_{role}",
                "stubBasename": f"{prefix}_{role}_anchor",
            }
            for role in PATTERN_ROLE_DIRS.get(pattern_key, ())
        }

    merge_pubspec_dependencies(pubspec, state_key)

    main_path = fp / "lib" / "main.dart"
    main_path.parent.mkdir(parents=True, exist_ok=True)
    main_path.write_text(generate_main_dart(prefix, dart_pkg), encoding="utf-8")
    written.append("lib/main.dart")

    if lib_layout == "dual_hub":
        _write_skin_files(
            lib_root / f"{prefix}_core",
            prefix=prefix,
            seg=seg,
            bucket_name=f"{prefix}_core",
            written=written,
        )
    else:
        _write_skin_files(
            lib_root / skin_bucket,
            prefix=prefix,
            seg=seg,
            bucket_name=skin_bucket,
            written=written,
        )

    if lib_layout == "flat_skin_role_helper":
        helper = lib_root / f"{prefix}_helper"
        helper.mkdir(parents=True, exist_ok=True)
        (helper / ".gitkeep").write_text("", encoding="utf-8")
        written.append(f"lib/{seg}/{prefix}_helper/.gitkeep")

    views_dir_name = _views_folder_basename(lock, prefix, pattern_key)

    if lib_layout == "single_lane":
        lane_dir = lib_root / f"{prefix}_lane"
        lane_dir.mkdir(parents=True, exist_ok=True)
        home_path = lane_dir / f"{prefix}_home_placeholder.dart"
        home_path.write_text(generate_home_placeholder(prefix), encoding="utf-8")
        written.append(f"lib/{seg}/{prefix}_lane/{prefix}_home_placeholder.dart")
        home_import = f"{seg}/{prefix}_lane/{prefix}_home_placeholder.dart"

        for role in PATTERN_ROLE_DIRS.get(pattern_key, ()):
            entry = folder_map.get(role, {})
            stub_name = (
                entry.get("stubBasename") or f"{prefix}_{role}_anchor"
            ).removesuffix(".dart")
            if role == "models" or role in PATTERN_ROLE_STUBS.get(
                pattern_key, {}
            ):
                stub_path = lane_dir / f"{stub_name}.dart"
                _write_stub(
                    stub_path,
                    role=role,
                    prefix=prefix,
                    entry=entry,
                    pattern_key=pattern_key,
                )
                written.append(f"lib/{seg}/{prefix}_lane/{stub_name}.dart")
    else:
        if lib_layout == "shell_bay":
            home_import = (
                f"{seg}/{views_dir_name}/{prefix}_bay/"
                f"{prefix}_home_placeholder.dart"
            )
        else:
            if lib_layout == "dual_hub":
                home_import = (
                    f"{seg}/{prefix}_surface/{views_dir_name}/"
                    f"{prefix}_home_placeholder.dart"
                )
            else:
                home_import = (
                    f"{seg}/{views_dir_name}/{prefix}_home_placeholder.dart"
                )

        for role in PATTERN_ROLE_DIRS.get(pattern_key, ()):
            entry = folder_map.get(role, {})
            folder_basename = entry.get("folderBasename") or f"{prefix}_{role}"
            role_dir = _role_parent(
                lib_root,
                lib_layout=lib_layout,
                prefix=prefix,
                role=role,
                folder_basename=folder_basename,
            )
            role_dir.mkdir(parents=True, exist_ok=True)
            rel_prefix = role_dir.relative_to(fp / "lib").as_posix()

            if role == "views":
                if lib_layout == "shell_bay":
                    bay = role_dir / f"{prefix}_bay"
                    bay.mkdir(parents=True, exist_ok=True)
                    home_path = bay / f"{prefix}_home_placeholder.dart"
                else:
                    home_path = role_dir / f"{prefix}_home_placeholder.dart"
                home_path.write_text(
                    generate_home_placeholder(prefix),
                    encoding="utf-8",
                )
                written.append(
                    f"lib/{home_path.relative_to(fp / 'lib').as_posix()}"
                )

            stub_name = (
                entry.get("stubBasename") or f"{prefix}_{role}_anchor"
            ).removesuffix(".dart")
            if role == "models" or role in PATTERN_ROLE_STUBS.get(
                pattern_key, {}
            ):
                stub_path = role_dir / f"{stub_name}.dart"
                _write_stub(
                    stub_path,
                    role=role,
                    prefix=prefix,
                    entry=entry,
                    pattern_key=pattern_key,
                )
                written.append(f"lib/{rel_prefix}/{stub_name}.dart")
            else:
                gitkeep = role_dir / ".gitkeep"
                if not gitkeep.is_file():
                    gitkeep.write_text("", encoding="utf-8")
                written.append(f"lib/{rel_prefix}/.gitkeep")

            _ensure_impl_subdir(
                role_dir,
                prefix=prefix,
                role=role,
                lib_layout=lib_layout,
                written=written,
                rel_prefix=f"lib/{rel_prefix}",
            )

    app_bucket = f"{prefix}_core" if lib_layout == "dual_hub" else skin_bucket
    app_path = lib_root / f"{prefix}_app.dart"
    app_path.parent.mkdir(parents=True, exist_ok=True)
    app_path.write_text(
        generate_app_dart(
            prefix,
            dart_pkg,
            state_key,
            home_import=home_import,
            skin_bucket=app_bucket,
        ),
        encoding="utf-8",
    )
    written.append(f"lib/{seg}/{prefix}_app.dart")

    for forbidden in PATTERN_FORBIDDEN_DIRS.get(pattern_key, ()):
        bad = lib_root / f"{prefix}_{forbidden}"
        if bad.is_dir():
            shutil.rmtree(bad)

    semantic_re = semantic_dir_pattern(prefix)
    if lib_root.is_dir():
        for child in list(lib_root.iterdir()):
            if child.is_dir() and semantic_re.match(child.name):
                shutil.rmtree(child)

    layout = refresh_tool_asset_manifest(workspace, lock)

    for root in layout.get("assetRoots") or []:
        asset_dir = fp / root
        asset_dir.mkdir(parents=True, exist_ok=True)
        gitkeep = asset_dir / ".gitkeep"
        if not gitkeep.is_file():
            gitkeep.write_text("", encoding="utf-8")

    write_resource_layout_manifest(workspace, layout)

    expected = expected_scaffold_paths(
        prefix,
        dart_pkg,
        pattern_key,
        folder_map,
        lib_layout=lib_layout,
        skin_bucket=skin_bucket,
    )
    update_scaffold_files(workspace, expected)
    _copy_reference_templates(workspace)
    return written


from batch.config import _project_root

_PROJECT_ROOT = _project_root()
_REFERENCE_TEMPLATES = (
    ("legal_web_view.dart.template", "legal_web_view.dart.template"),
    ("keyboard_dismiss.dart.template", "keyboard_dismiss.dart.template"),
)


def _copy_reference_templates(workspace: Path) -> None:
    """Copy Agent reference snippets into app workspace (Phase 3)."""
    templates_dir = _PROJECT_ROOT / "data" / "static" / "templates"
    for src_name, dest_name in _REFERENCE_TEMPLATES:
        src = templates_dir / src_name
        if not src.is_file():
            continue
        dest = workspace / dest_name
        if dest.is_file():
            continue
        try:
            shutil.copy2(src, dest)
        except OSError:
            pass
