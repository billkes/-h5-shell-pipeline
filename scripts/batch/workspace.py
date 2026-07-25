"""Workspace preparation: copy docs, layout manifest."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from batch.config import BatchConfig
from batch.iap_catalog import setup_iap_workspace
from batch.pack_type import is_h5_shell
from batch.ui_compliance import IAP_SOURCE, copy_iap_spec_file

CURSOR_UUPM_SKILL_REL = Path(".cursor/skills/ui-ux-pro-max")
CURSOR_UUPM_SCRIPT_PREFIX = ".cursor/skills/ui-ux-pro-max/scripts/"
DEFAULT_UUPM_SKILL_GIT_URL = (
    "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git"
)
SIBLING_SKILL_NAMES: tuple[str, ...] = (
    "brand",
    "design-system",
    "design",
    "ui-styling",
)

# Closed corpus for H5 Agents — all copied into the package workspace root.
# Do NOT include pipeline-only docs/rules/* (theme firewall, task-init, etc.).
H5_SHELL_WORKSPACE_DOCS: tuple[str, ...] = (
    "H5壳Flutter产品要求.md",
    "H5壳Plan交付规范.md",
    "H5壳Pack约束.md",
    "H5壳Micro-UI Kit约束.md",
    "H5壳H5实现检查清单.md",
    "H5壳功能文档深度标准.md",
    "H5壳交互拓扑与PlanGate策略.md",
    "H5壳产品文档格式.md",
    "H5-Bridge协议.md",
    "H5壳业务流程文字版.md",
    "H5去风味规范.md",
    "H5壳IAP协议.md",
    "H5壳Legal弹层规范.md",
    "H5壳Vite工程规范.md",
    "H5壳ui-ux-pro-max使用规范.md",
    "H5壳Overlay路由规范.md",
    "H5壳广场页规范.md",
    "H5壳启动闪屏规范.md",
    "H5壳Swift实现规范.md",
    "H5壳OC实现规范.md",
    "H5壳Vault合规维护规范.md",
    "H5壳WKWebView性能与层叠规范.md",
    "法律协议规范.md",
)

H5_SNIPPETS_BRIDGE_REL = Path("data/static/h5_snippets/bridge")
H5_SNIPPETS_LEGAL_REL = Path("data/static/h5_snippets/legal")


def _rm_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    shutil.rmtree(path)


def _copytree_replace(src: Path, dest: Path) -> None:
    """Copy ``src`` → ``dest`` as real files (never leave a symlink)."""
    _rm_path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)


def _skill_search_ready(skill_dir: Path) -> bool:
    """True when skill is a real in-workspace tree (not an external symlink)."""
    search = skill_dir / "scripts" / "search.py"
    if not search.is_file():
        return False
    if skill_dir.is_symlink() or (skill_dir / "scripts").is_symlink():
        return False
    if (skill_dir / "data").is_symlink():
        return False
    return True


def _uupm_git_settings(cfg: BatchConfig) -> tuple[str, str]:
    """Return (git_url, git_ref). Empty ref → clone default branch."""
    url = (getattr(cfg, "uupm_skill_git_url", "") or "").strip()
    ref = (getattr(cfg, "uupm_skill_git_ref", "") or "").strip()
    env_url = (os.environ.get("UUPM_SKILL_GIT_URL") or "").strip()
    env_ref = (os.environ.get("UUPM_SKILL_GIT_REF") or "").strip()
    if env_url:
        url = env_url
    if env_ref:
        ref = env_ref
    yaml_path = cfg.config_dir / "config.yaml"
    if yaml_path.is_file() and (not url or not ref):
        try:
            import yaml

            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            uupm = data.get("uupm") if isinstance(data, dict) else None
            if isinstance(uupm, dict):
                if not url:
                    url = str(uupm.get("skill_git_url") or "").strip()
                if not ref:
                    ref = str(uupm.get("skill_git_ref") or "").strip()
        except Exception:
            pass
    if not url:
        url = DEFAULT_UUPM_SKILL_GIT_URL
    return url, ref


def _git_clone_skill_repo(url: str, ref: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd.extend(["--branch", ref])
    cmd.extend([url, str(dest)])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode == 0 and dest.is_dir():
        return True
    # Retry without --branch when ref is a commit SHA or missing remote branch.
    if ref:
        _rm_path(dest)
        proc2 = subprocess.run(
            ["git", "clone", url, str(dest)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc2.returncode != 0:
            print(f"  >>> git clone 失败: {proc.stderr or proc.stdout or proc2.stderr}")
            return False
        chk = subprocess.run(
            ["git", "-C", str(dest), "checkout", ref],
            capture_output=True,
            text=True,
            check=False,
        )
        if chk.returncode != 0:
            print(f"  >>> git checkout {ref} 失败: {chk.stderr or chk.stdout}")
            return False
        return True
    print(f"  >>> git clone 失败: {proc.stderr or proc.stdout}")
    return False


def _skill_bundle_from_repo(repo_root: Path) -> Path | None:
    """Prefer Claude skill bundle; fall back to src/ui-ux-pro-max package."""
    claude = repo_root / ".claude" / "skills" / "ui-ux-pro-max"
    if (claude / "scripts" / "search.py").is_file():
        return claude
    nested = repo_root / "src" / "ui-ux-pro-max"
    if (nested / "scripts" / "search.py").is_file():
        return nested
    if (repo_root / "scripts" / "search.py").is_file():
        return repo_root
    return None


def _cursor_uupm_skill_md(skill_dir: Path, repo_root: Path | None) -> str:
    """Render SKILL.md with workspace-relative script paths."""
    source = skill_dir / "SKILL.md"
    if not source.is_file() and repo_root is not None:
        alt = repo_root / ".claude" / "skills" / "ui-ux-pro-max" / "SKILL.md"
        if alt.is_file():
            source = alt
    if source.is_file():
        text = source.read_text(encoding="utf-8")
    else:
        text = (
            "---\n"
            "name: ui-ux-pro-max\n"
            "description: UI/UX design intelligence (vendored into app workspace).\n"
            "---\n\n"
            "# UI/UX Pro Max\n\n"
            "Run search from this app workspace root:\n\n"
        )
    for old in (
        "python3 skills/ui-ux-pro-max/scripts/",
        "python3 .claude/skills/ui-ux-pro-max/scripts/",
        "python .claude/skills/ui-ux-pro-max/scripts/",
    ):
        text = text.replace(old, f"python {CURSOR_UUPM_SCRIPT_PREFIX}")
    text = text.replace(
        f"python3 {CURSOR_UUPM_SCRIPT_PREFIX}",
        f"python {CURSOR_UUPM_SCRIPT_PREFIX}",
    )
    return text


def _materialize_uupm_from_bundle(
    workspace: Path, bundle: Path, repo_root: Path | None
) -> bool:
    skill_dir = workspace / CURSOR_UUPM_SKILL_REL
    _copytree_replace(bundle, skill_dir)
    # If bundle was src/ui-ux-pro-max without SKILL.md, still write one.
    (skill_dir / "SKILL.md").write_text(
        _cursor_uupm_skill_md(skill_dir, repo_root),
        encoding="utf-8",
    )
    return _skill_search_ready(skill_dir)


def _copy_sibling_skills(workspace: Path, repo_root: Path) -> int:
    skills_root = workspace / ".cursor" / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    copied = 0
    for name in SIBLING_SKILL_NAMES:
        src = repo_root / ".claude" / "skills" / name
        if not src.is_dir():
            continue
        _copytree_replace(src, skills_root / name)
        copied += 1
    return copied


def ensure_workspace_skills(cfg: BatchConfig, workspace: Path) -> bool:
    """Vendor ui-ux-pro-max (+ optional siblings) as real files under ``.cursor/skills/``."""
    from batch.skill_resolve import integration_enabled

    ok = ensure_cursor_uupm_skill(cfg, workspace)
    if not ok:
        return False
    if not integration_enabled(cfg, "sibling_skills_link"):
        return True
    # Siblings are copied during the same clone/copy pass inside ensure_cursor_uupm_skill
    # when a repo root is available; if skill was already ready, try local repo once.
    skill_dir = workspace / CURSOR_UUPM_SKILL_REL
    if any((workspace / ".cursor" / "skills" / n).is_dir() for n in SIBLING_SKILL_NAMES):
        return True
    try:
        from batch.skill_resolve import resolve_skill_repo_root

        repo_root = resolve_skill_repo_root(cfg)
    except RuntimeError:
        return True
    if repo_root is None:
        return True
    n = _copy_sibling_skills(workspace, repo_root)
    if n:
        print(
            ">>> 已复制兄弟 skills → "
            ".cursor/skills/{brand,design-system,design,ui-styling}"
        )
    _ = skill_dir
    return True


def ensure_cursor_uupm_skill(cfg: BatchConfig, workspace: Path) -> bool:
    """Clone/copy ui-ux-pro-max into the app workspace (real files, web-Agent safe)."""
    from batch.skill_resolve import integration_enabled

    skill_dir = workspace / CURSOR_UUPM_SKILL_REL
    if _skill_search_ready(skill_dir):
        print(f">>> Cursor skill 已就绪（包内）: {CURSOR_UUPM_SKILL_REL}")
        return True

    url, ref = _uupm_git_settings(cfg)
    print(f">>> 克隆 ui-ux-pro-max-skill → 包内 {CURSOR_UUPM_SKILL_REL}")
    print(f"    url={url}" + (f" ref={ref}" if ref else ""))

    with tempfile.TemporaryDirectory(prefix="uupm-skill-") as td:
        clone_dest = Path(td) / "ui-ux-pro-max-skill"
        if _git_clone_skill_repo(url, ref, clone_dest):
            bundle = _skill_bundle_from_repo(clone_dest)
            if bundle is not None and _materialize_uupm_from_bundle(
                workspace, bundle, clone_dest
            ):
                if integration_enabled(cfg, "sibling_skills_link"):
                    n = _copy_sibling_skills(workspace, clone_dest)
                    if n:
                        print(
                            ">>> 已克隆兄弟 skills → "
                            ".cursor/skills/{brand,design-system,design,ui-styling}"
                        )
                print(f">>> 已克隆 Cursor skill → {CURSOR_UUPM_SKILL_REL}")
                return True

    # Offline bootstrap: copy from local skill_dir / sibling checkout (vendoring only).
    try:
        from batch.skill_resolve import resolve_skill_repo_root, resolve_uupm_package_dir

        repo_root = resolve_skill_repo_root(cfg)
        package = resolve_uupm_package_dir(cfg)
    except RuntimeError as exc:
        print(f"  >>> 跳过 Cursor skill 克隆/复制: {exc}")
        return False

    bundle = None
    if repo_root is not None:
        bundle = _skill_bundle_from_repo(repo_root)
    if (
        bundle is None
        and package is not None
        and (package / "scripts" / "search.py").is_file()
    ):
        bundle = package
    if bundle is None:
        print("  >>> 找不到可复制的 ui-ux-pro-max skill bundle")
        return False
    if not _materialize_uupm_from_bundle(workspace, bundle, repo_root):
        return False
    if repo_root is not None and integration_enabled(cfg, "sibling_skills_link"):
        n = _copy_sibling_skills(workspace, repo_root)
        if n:
            print(
                ">>> 已复制兄弟 skills → "
                ".cursor/skills/{brand,design-system,design,ui-styling}"
            )
    print(f">>> 已复制 Cursor skill（本地源）→ {CURSOR_UUPM_SKILL_REL}")
    return True


def copy_component_kit_to_workspace(cfg: BatchConfig, workspace: Path) -> None:
    """Copy data/static/component_kit/ into workspace so agents can read kit docs."""
    src = cfg.project_dir / "data" / "static" / "component_kit"
    if not src.is_dir():
        return
    dest = workspace / "data" / "static" / "component_kit"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def copy_h5_bridge_snippets_to_workspace(cfg: BatchConfig, workspace: Path) -> None:
    """Copy browser Bridge mock snippet into the package (closed corpus)."""
    src = cfg.project_dir / H5_SNIPPETS_BRIDGE_REL
    if not src.is_dir():
        return
    dest = workspace / H5_SNIPPETS_BRIDGE_REL
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)


def copy_h5_legal_snippets_to_workspace(cfg: BatchConfig, workspace: Path) -> None:
    """Copy legalLinks runtime-branch snippet into the package (closed corpus)."""
    src = cfg.project_dir / H5_SNIPPETS_LEGAL_REL
    if not src.is_dir():
        return
    dest = workspace / H5_SNIPPETS_LEGAL_REL
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)


def write_layout_manifest(workspace: Path, dart_pkg: str) -> None:
    combo = workspace / "本包代码组合.json"
    if not combo.is_file():
        return
    try:
        prefix = (
            json.loads(combo.read_text(encoding="utf-8"))
            .get("dartCodePrefix")
            or ""
        ).strip()
    except json.JSONDecodeError:
        return
    if not prefix:
        return
    root = f"{prefix}_{dart_pkg}"
    lines = [
        "# Auto-generated by batch script. Phase 2 MUST follow.",
        f"DART_CODE_PREFIX={prefix}",
        f"LIB_ROOT_SEGMENT={root}",
        f"LIB_ROOT_FOLDER=lib/{root}/",
        "FORBIDDEN_LIB_DIR_BASENAMES=screens,widgets,models,services,"
        "controllers,core,pages,utils,common,components,helpers,data,base",
        "NESTED_THEME_SUBDIRS_MIN=2",
        "LIB_ROOT_MAX_DART_FILES=4",
        "FORBIDDEN_NAME_FRAGMENTS=_screen,_screens,_model,_models,_widget,"
        "_widgets,_service,_services,_controller,_controllers,_page,_pages",
    ]
    (workspace / "主题代码布局.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def alloc_code_combo(cfg: BatchConfig, workspace: Path) -> None:
    """Allocate 本包代码组合.json (skip if already valid — matches 2.0 phase2)."""
    combo = workspace / "本包代码组合.json"
    if combo.is_file():
        try:
            prefix = (
                json.loads(combo.read_text(encoding="utf-8"))
                .get("dartCodePrefix")
                or ""
            ).strip()
            if prefix:
                return
        except json.JSONDecodeError:
            pass
    script = cfg.scripts_dir / "alloc_code_combo.py"
    if not script.is_file():
        raise FileNotFoundError(
            f"缺少代码组合分配脚本: {script} "
            f"（无法生成 {combo.name}）"
        )
    result = subprocess.run(
        [sys.executable, str(script), str(cfg.contentpack_registry), str(workspace)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"alloc_code_combo 失败 (exit {result.returncode}): {err or '无输出'}"
        )
    if not combo.is_file():
        raise RuntimeError(
            f"alloc_code_combo 未生成 {combo.name}，工作区: {workspace}"
        )


def code_combo_block(workspace: Path) -> str:
    combo = workspace / "本包代码组合.json"
    if not combo.is_file():
        return ""
    try:
        data = json.loads(combo.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    lines = [
        "[Code & Structure — ASSIGNED for this package; "
        "you MUST document and use these exactly]"
    ]
    has_csv_pattern = bool(data.get("architecturePattern"))
    for key, val in data.items():
        note = ""
        if has_csv_pattern and key == "architecture":
            note = (
                "   (anti-correlation tag only; code STRUCTURE is governed "
                "by architecturePattern below)"
            )
        elif has_csv_pattern and key == "folderStyle":
            note = "   (anti-correlation tag only; see architecturePattern)"
        lines.append(f"- {key}: {val}{note}")
    return "\n".join(lines)


def dart_prefix(workspace: Path, default: str = "apxxx") -> str:
    combo = workspace / "本包代码组合.json"
    if not combo.is_file():
        return default
    try:
        val = (
            json.loads(combo.read_text(encoding="utf-8"))
            .get("dartCodePrefix")
            or ""
        ).strip()
        return val or default
    except json.JSONDecodeError:
        return default


def copy_workspace_docs(
    cfg: BatchConfig,
    workspace: Path,
    app_name: str,
    pack_type: str,
    *,
    first_product_code: str = "",
) -> None:
    docs = cfg.docs_dir
    mapping = [
        (docs / "Flutter差异化开发规则.md", workspace),
        (docs / "Flutter UI规范.md", workspace),
        (docs / "暗黑模式与对比度规范.md", workspace),
    ]
    if pack_type == "videostream":
        mapping.append((docs / "视频流包产品要求.md", workspace))
    elif pack_type == "tool_flutter":
        mapping.append((docs / "工具包Flutter产品要求.md", workspace))
    elif is_h5_shell(pack_type):
        for name in H5_SHELL_WORKSPACE_DOCS:
            src = docs / name
            if src.is_file():
                mapping.append((src, workspace))
    else:
        mapping.append((docs / "图文包产品要求.md", workspace))
    for src, dest in mapping:
        if src.is_file():
            shutil.copy2(src, dest / src.name)
    docs_src = cfg.project_dir / "docs"
    for name in (
        "架构模式配对矩阵.md",
        "状态管理矩阵.md",
        "架构模式矩阵.md",
        "编程人设风格.md",
        "命名混淆规则.md",
        "产品文档规范.md",
    ):
        src = docs_src / name
        if src.is_file():
            shutil.copy2(src, workspace / name)
    setup_iap_workspace(
        project_dir=cfg.project_dir,
        docs_dir=cfg.docs_dir,
        workspace=workspace,
        first_product_code=first_product_code,
    )
    copy_iap_spec_file(cfg.project_dir / IAP_SOURCE, workspace)
    copy_component_kit_to_workspace(cfg, workspace)
    if is_h5_shell(pack_type):
        copy_h5_bridge_snippets_to_workspace(cfg, workspace)
        copy_h5_legal_snippets_to_workspace(cfg, workspace)
    ensure_workspace_skills(cfg, workspace)
    if getattr(cfg, "iap_bundle_prefix", ""):
        print(
            "  >>> 注意: IAP_BUNDLE_PREFIX 已废弃于商品表；"
            "productId 以 iap-catalog.generated.md 为准"
        )


def ensure_flutter_create(workspace: Path, dart_name: str) -> bool:
    pubspec = workspace / "pubspec.yaml"
    if pubspec.is_file():
        print(">>> pubspec.yaml 已存在，跳过 flutter create")
        return True
    result = subprocess.run(
        ["flutter", "create", "--platforms=ios", f"--project-name={dart_name}", "."],
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(">>> flutter create 完成")
    else:
        print("警告: flutter create 失败，Phase 2 将由 agent 自行创建工程结构")
    return pubspec.is_file()


def patch_pubspec_overrides(workspace: Path) -> None:
    """Inject dependency_overrides for record_linux (iOS build fix).

    record 5.x pulls record_linux 0.7.2 which lacks startStream; Flutter
    compiles all platform implementations and fails iOS builds. Idempotent.
    """
    pubspec = workspace / "pubspec.yaml"
    if not pubspec.is_file():
        return
    content = pubspec.read_text(encoding="utf-8")
    if re.search(r"^\s*record_linux\s*:", content, re.MULTILINE):
        return
    override_block = (
        "\ndependency_overrides:\n"
        "  record_linux: ^1.3.0\n"
    )
    if "dependency_overrides:" in content:
        content = re.sub(
            r"(?m)^dependency_overrides:\s*\n",
            "dependency_overrides:\n  record_linux: ^1.3.0\n",
            content,
            count=1,
        )
    else:
        content = content.rstrip() + override_block
    pubspec.write_text(content, encoding="utf-8")
    print(">>> 已在 pubspec.yaml 中添加 record_linux dependency_overrides")


def read_verification_issues(workspace: Path) -> str:
    """Summarize Phase 2/3 verification-report.md issues for Agent prompts."""
    report = workspace / "verification-report.md"
    if not report.is_file():
        return ""
    text = report.read_text(encoding="utf-8", errors="replace")
    if "**结果: 通过**" in text:
        return ""
    issues: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            issues.append(stripped[2:].strip())
    if not issues:
        return ""
    body = "\n".join(f"- {item}" for item in issues)
    return (
        "[Phase 2 Verification Issues — FIX during this pass]\n"
        "The following were detected after Phase 3; fix them now (rename files, "
        "update imports, adjust structure). Do not ignore:\n"
        f"{body}\n"
    )


from batch.dimension_lock import resolve_dimension_lock
from batch.flutter_ops import find_flutter_project
from batch.programming_layout import layout_from_lock


def ensure_pubspec_assets(workspace: Path) -> None:
    fp = find_flutter_project(workspace) or workspace
    pubspec = fp / "pubspec.yaml"
    if not pubspec.is_file():
        return
    layout = layout_from_lock(resolve_dimension_lock(workspace))
    roots = layout.get("assetRoots") or ["assets/images/"]
    roots = [r if r.endswith("/") else f"{r}/" for r in roots]
    content = pubspec.read_text(encoding="utf-8")
    missing = [
        r
        for r in roots
        if r.rstrip("/") not in content.replace(" ", "")
    ]
    if missing:
        if re.search(r"^\s{2}assets:\s*$", content, re.MULTILINE):
            insert = "".join(f"    - {r}\n" for r in missing)
            content = re.sub(
                r"(^  assets:\s*\n(?:    - .+\n)*)",
                lambda m: m.group(1) + insert,
                content,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            block = "  assets:\n" + "".join(f"    - {r}\n" for r in roots)
            content = re.sub(
                r"(^flutter:\s*\n)",
                rf"\1{block}",
                content,
                count=1,
                flags=re.MULTILINE,
            )
        pubspec.write_text(content, encoding="utf-8")
        print(f">>> 已在 pubspec.yaml 中声明资源目录: {', '.join(roots)}")
    for root in roots:
        (fp / root).mkdir(parents=True, exist_ok=True)


def fix_xcode_project_settings(
    ios_root: Path,
    *,
    app_name: str = "",
    bundle_id_prefix: str = "",
) -> None:
    """Limit destinations to iPhone and remove SceneDelegate artifacts."""
    pbx_files = [
        p
        for p in ios_root.rglob("project.pbxproj")
        if "build" not in p.parts and "DerivedData" not in p.parts
    ]
    if not pbx_files:
        return
    pbx = pbx_files[0]
    text = pbx.read_text(encoding="utf-8", errors="replace")
    replacements = {
        "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD = YES": (
            "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD = NO"
        ),
        "SUPPORTS_MACCATALYST = YES": "SUPPORTS_MACCATALYST = NO",
        "SUPPORTS_XR_DESIGNED_FOR_IPHONE_IPAD = YES": (
            "SUPPORTS_XR_DESIGNED_FOR_IPHONE_IPAD = NO"
        ),
        'TARGETED_DEVICE_FAMILY = "1,2"': "TARGETED_DEVICE_FAMILY = 1",
        "TARGETED_DEVICE_FAMILY = 1,2": "TARGETED_DEVICE_FAMILY = 1",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(
        r"IPHONEOS_DEPLOYMENT_TARGET = [^;]+;",
        "IPHONEOS_DEPLOYMENT_TARGET = 13.0;",
        text,
    )

    if bundle_id_prefix and app_name:
        slug = re.sub(r"[^a-z0-9]", "", app_name.lower())
        target = f"{bundle_id_prefix}.{slug}"
        text = re.sub(
            r'PRODUCT_BUNDLE_IDENTIFIER = "[^"]*"',
            f'PRODUCT_BUNDLE_IDENTIFIER = "{target}"',
            text,
        )
        text = re.sub(
            r"PRODUCT_BUNDLE_IDENTIFIER = [^;]*;",
            f'PRODUCT_BUNDLE_IDENTIFIER = "{target}";',
            text,
        )
        print(f"  >>> Bundle ID 已设为 {target}")

    pbx.write_text(text, encoding="utf-8")

    for pattern in ("SceneDelegate.swift", "SceneDelegate.m", "SceneDelegate.h"):
        for path in ios_root.rglob(pattern):
            if "build" in path.parts:
                continue
            path.unlink(missing_ok=True)

    plist_files = [
        p
        for p in ios_root.rglob("Info.plist")
        if "build" not in p.parts and "Pods" not in p.parts
    ]
    if plist_files:
        try:
            import plistlib

            plist = plist_files[0]
            with plist.open("rb") as f:
                data = plistlib.load(f)
            if "UIApplicationSceneManifest" in data:
                del data["UIApplicationSceneManifest"]
                with plist.open("wb") as f:
                    plistlib.dump(data, f)
        except (OSError, ValueError, ImportError):
            pass
