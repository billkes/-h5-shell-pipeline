"""H5 default seed data gate — 编组 I: silent bootstrap on first launch."""

from __future__ import annotations

import re
from pathlib import Path

from batch.h5_shell_placeholders import prefix_from_workspace
from batch.h5_vite_gate import h5_src_dir, is_h5_vite_project
from batch.h5_vite_scaffold import TEMPLATE_ROOT, resolve_prefix, substitute_text, template_values
from batch.native_bundled_media import (
    collect_native_bundled_media_violations,
    native_bundled_img_dir,
    requires_native_bundled_media,
)
from batch.screen_inventory import read_spec_text

_BOOTSTRAP_CALL_RE = re.compile(r"\bensureBootstrapData\s*\(|\bbootstrapSeed\s*\(")
_VAULT_REF_RE = re.compile(
    r"""vaultAssetPath\s*\(\s*['"]([^'"]+)['"]\s*\)|assets/img/([^'"\s]+)|assets/[a-z0-9]+_vault/([^'"\s]+)""",
    re.I,
)
_DEMO_DATA_MARKERS = (
    "演示数据",
    "静默预置",
    "first launch",
    "bootstrap",
    "默认数据",
    "首发数据",
    "编组 i",
    "编组i",
    "default seed",
)


def _product_text(project: Path) -> str:
    parts: list[str] = [read_spec_text(project)]
    for path in sorted(project.glob("*.md")):
        if path.name == "功能文档.md":
            continue
        try:
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(parts)


def _router_text(project: Path) -> str:
    router = h5_src_dir(project) / "router" / "index.ts"
    if not router.is_file():
        return ""
    try:
        return router.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def requires_default_seed(project: Path) -> bool:
    """True when product doc or route topology expects first-launch bundled seed."""
    blob = _product_text(project).lower()
    if any(marker in blob for marker in _DEMO_DATA_MARKERS):
        return True
    routes = _router_text(project)
    if not routes:
        return False
    has_welcome = "/welcome" in routes or "WelcomeView" in routes
    has_lists = any(
        token in routes
        for token in ("/hub", "/runs", "/insights", "HubView", "RunsView", "InsightsView")
    )
    return has_welcome and has_lists


def _extract_function_body(text: str, name: str) -> str:
    match = re.search(
        rf"(?:export\s+)?function\s+{re.escape(name)}\s*\([^)]*\)(?:\s*:[^{{]+)?\s*\{{",
        text,
    )
    if not match:
        return ""
    start = match.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return text[start : i - 1] if depth == 0 else ""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def collect_h5_default_seed_violations(project: Path) -> list[str]:
    """Hard gate: defaultSeed module, Welcome wiring, vault assets, clear-data pin."""
    if not is_h5_vite_project(project) or not requires_default_seed(project):
        return []

    issues: list[str] = []
    src = h5_src_dir(project)
    seed_path = src / "store" / "defaultSeed.ts"
    if not seed_path.is_file():
        issues.append("缺少 h5/src/store/defaultSeed.ts（产品要求首次打开预置默认数据）")
        return issues

    seed_text = _read_text(seed_path)
    if "ensureBootstrapData" not in seed_text:
        issues.append("defaultSeed.ts 须导出 ensureBootstrapData()")
    if "BOOTSTRAP_KEY" not in seed_text:
        issues.append("defaultSeed.ts 须定义 BOOTSTRAP_KEY")

    plans_body = _extract_function_body(seed_text, "buildDefaultPlans")
    if not plans_body and "buildDefaultPlans" not in seed_text:
        issues.append("defaultSeed.ts 须定义 buildDefaultPlans()")
    elif plans_body.count("title:") < 1:
        issues.append("buildDefaultPlans() 须预置至少 1 条草稿（含 title 字段）")

    runs_body = _extract_function_body(seed_text, "buildDefaultRuns")
    if "buildDefaultRuns" in seed_text and runs_body.count("planId:") < 1:
        issues.append("buildDefaultRuns() 须预置至少 1 条 run（含 planId 字段）")

    welcome_logic = src / "views" / "WelcomeView.logic.ts"
    if welcome_logic.is_file():
        wl = _read_text(welcome_logic)
        if "continueFlow" not in wl or not _BOOTSTRAP_CALL_RE.search(wl):
            issues.append("WelcomeView.logic.ts continueFlow 须调用 ensureBootstrapData()")
    elif (src / "views" / "SplashView.vue").is_file():
        splash = _read_text(src / "views" / "SplashView.vue")
        if not _BOOTSTRAP_CALL_RE.search(splash):
            issues.append("Splash→Hub 路径须调用 ensureBootstrapData()（缺 WelcomeView.logic.ts）")
    else:
        issues.append("须有 WelcomeView.logic.ts 或在 Splash 首次进 Hub 前挂载 ensureBootstrapData()")

    settings_logic = src / "views" / "SettingsView.logic.ts"
    if settings_logic.is_file() and "clearData" in _read_text(settings_logic):
        st = _read_text(settings_logic)
        if "BOOTSTRAP_KEY" not in st and "_bootstrap_v1" not in st:
            issues.append(
                "SettingsView.logic.ts clearData 须写入 BOOTSTRAP_KEY，清空后禁止自动再灌数"
            )

    prefix = prefix_from_workspace(project) or resolve_prefix(project) or "app"
    ws = project.resolve()
    vault_dir = native_bundled_img_dir(ws) if requires_native_bundled_media(ws) else (
        ws / "h5" / "assets" / f"{prefix}_vault"
    )
    vault_label = (
        str(vault_dir.relative_to(ws))
        if vault_dir is not None and vault_dir.is_relative_to(ws)
        else f"h5/assets/{prefix}_vault"
    )
    for match in _VAULT_REF_RE.finditer(seed_text):
        fname = (match.group(1) or match.group(2) or match.group(3) or "").strip()
        if fname and vault_dir is not None and not (vault_dir / fname).is_file():
            issues.append(f"defaultSeed 引用 bundled 配图缺失: {vault_label}/{fname}")

    issues.extend(collect_native_bundled_media_violations(project))

    return issues

def sync_default_seed_stub(
    project: Path,
    *,
    app_name: str = "",
    write: bool = True,
) -> Path | None:
    """Copy defaultSeed.ts.tpl when product requires seed and module is missing."""
    if not is_h5_vite_project(project) or not requires_default_seed(project):
        return None
    dst = h5_src_dir(project) / "store" / "defaultSeed.ts"
    if dst.is_file():
        return None
    tpl = TEMPLATE_ROOT / "src" / "store" / "defaultSeed.ts.tpl"
    if not tpl.is_file():
        return None
    if not app_name:
        app_name = project.name
    prefix = resolve_prefix(project)
    values = template_values(project, app_name=app_name, prefix=prefix)
    body = substitute_text(tpl.read_text(encoding="utf-8"), values)
    if write:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(body, encoding="utf-8")
    return dst


def sync_settings_clear_bootstrap(
    project: Path,
    *,
    app_name: str = "",
    write: bool = True,
) -> Path | None:
    """Scaffold SettingsView.logic.ts with BOOTSTRAP_KEY clear when file is absent."""
    if not is_h5_vite_project(project) or not requires_default_seed(project):
        return None
    routes = _router_text(project)
    if "/settings" not in routes and "SettingsView" not in routes:
        return None
    dst = h5_src_dir(project) / "views" / "SettingsView.logic.ts"
    if dst.is_file():
        return None
    tpl = TEMPLATE_ROOT / "pages" / "settings.logic.ts.tpl"
    if not tpl.is_file():
        return None
    if not app_name:
        app_name = project.name
    prefix = resolve_prefix(project)
    values = template_values(project, app_name=app_name, prefix=prefix)
    body = substitute_text(tpl.read_text(encoding="utf-8"), values)
    if write:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(body, encoding="utf-8")
    return dst
