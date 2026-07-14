"""Preview.tabs fidelity gates — theme truth, DOM markers, seed/KPI contract."""

from __future__ import annotations

import json
import re
from pathlib import Path

from batch.h5_site_paths import app_slug_from_name
from batch.h5_theme_tokens import THEME_START, resolve_prefix
from batch.h5_vite_gate import h5_src_dir, is_h5_vite_project
from batch.preview_tabs import (
    preview_canonical_path,
    preview_dir,
    preview_approved_colors_path,
    preview_html_path,
)

PREVIEW_IMPL_LOCK = "<!-- PREVIEW-IMPL:locked -->"

_HEX_RE = re.compile(r"#(?:[0-9A-Fa-f]{3}){1,2}\b")

TAB_ROOT_MARKERS: dict[str, tuple[str, ...]] = {
    "hub": (
        "home-hero",
        "float-sheet",
        "board-path",
        "tile-legend",
        "segment",
        "cta-game",
    ),
    "list": (
        "pick-row",
        "compare-header",
        "bar-compare",
        "delta-ribbon",
    ),
    "settings": (
        "settings-top",
        "settings-hero",
        "wallet-duo",
        "settings-block",
    ),
}

_KPI_MAGIC_RE = re.compile(r"\|\|\s*(?:8|240|4|50)")


def has_preview_artifacts(project: Path, app_name: str = "") -> bool:
    project = project.expanduser().resolve()
    if not preview_dir(project).is_dir():
        return False
    if app_name and preview_html_path(project, app_name).is_file():
        return True
    return any(p.name.endswith("-tabs-preview.html") for p in preview_dir(project).iterdir())


def _canonical_colors_section(text: str) -> str:
    m = re.search(r"^##\s*Colors\b[\s\S]*?(?=^##\s|\Z)", text, re.MULTILINE | re.IGNORECASE)
    return m.group(0) if m else ""


def _parse_mode_table(section: str, mode: str) -> dict[str, str]:
    out: dict[str, str] = {}
    block_m = re.search(
        rf"###\s*{re.escape(mode)}\s*mode\b([\s\S]*?)(?=###|\Z)",
        section,
        re.IGNORECASE,
    )
    if not block_m:
        return out
    block = block_m.group(1)
    for row in re.finditer(
        r"\|\s*([a-z][\w-]*)\s*\|\s*`?(#[0-9A-Fa-f]{3,8})`?\s*\|",
        block,
        re.I,
    ):
        out[row.group(1).lower()] = row.group(2).upper()
    return out


def _parse_tile_palette(section: str) -> dict[str, str]:
    tiles: dict[str, str] = {}
    m = re.search(r"\*\*Tile palette[^*]*\*\*[^\n]*", section, re.I)
    if not m:
        return tiles
    line = m.group(0)
    for m in re.finditer(
        r"(challenge|gift|trap|safe|fate|shop)\s*`?(#[0-9A-Fa-f]{3,8})`?",
        line,
        re.I,
    ):
        tiles[f"tile-{m.group(1).lower()}"] = m.group(2).upper()
    return tiles


def parse_colors_from_canonical(project: Path) -> dict[str, dict[str, str]]:
    path = preview_canonical_path(project)
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    section = _canonical_colors_section(text)
    if not section:
        return {}
    light = _parse_mode_table(section, "Light")
    dark = _parse_mode_table(section, "Dark")
    tiles = _parse_tile_palette(section)
    if tiles:
        light = {**light, **tiles}
        dark = {**dark, **tiles}
    payload: dict[str, dict[str, str]] = {}
    if light:
        payload["light"] = light
    if dark:
        payload["dark"] = dark
    return payload


def sync_preview_approved_colors_from_canonical(project: Path, *, write: bool = True) -> Path | None:
    """Deterministic colors.json from preview-canonical §Colors."""
    project = project.expanduser().resolve()
    parsed = parse_colors_from_canonical(project)
    if not parsed.get("light") or not parsed.get("dark"):
        return None
    dest = preview_approved_colors_path(project)
    body = json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
    if write:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
    return dest


def verify_preview_approved_colors(project: Path, app_name: str = "") -> list[str]:
    issues: list[str] = []
    if not has_preview_artifacts(project, app_name):
        return issues
    path = preview_approved_colors_path(project)
    if not path.is_file():
        issues.append("preview: 缺少 skill-adapt/preview-approved-colors.json（须含 light + dark）")
        return issues
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        issues.append("preview: preview-approved-colors.json 不是合法 JSON")
        return issues
    if not isinstance(data, dict):
        issues.append("preview: preview-approved-colors.json 须为对象")
        return issues
    light = data.get("light")
    dark = data.get("dark")
    if not isinstance(light, dict) or not light.get("primary"):
        issues.append("preview: preview-approved-colors.json 缺少 light.primary")
    if not isinstance(dark, dict) or not dark.get("primary"):
        issues.append("preview: preview-approved-colors.json 缺少 dark.primary")
    canonical = parse_colors_from_canonical(project)
    canon_primary = (canonical.get("light") or {}).get("primary", "").upper()
    if canon_primary and isinstance(light, dict):
        got = str(light.get("primary", "")).upper()
        if got and got != canon_primary:
            issues.append(
                f"preview: light.primary {got} 与 preview-canonical {canon_primary} 不一致"
            )
    return issues


def verify_preview_theme_drift(project: Path) -> list[str]:
    issues: list[str] = []
    if not has_preview_artifacts(project):
        return issues
    issues.extend(verify_preview_approved_colors(project))
    css_path = project / "h5" / "src" / "styles" / "global.css"
    if not css_path.is_file():
        issues.append("preview: 缺少 h5/src/styles/global.css")
        return issues
    css = css_path.read_text(encoding="utf-8", errors="ignore")
    if css.count(THEME_START) > 1:
        issues.append("preview: global.css 存在重复 THEME:pipeline 块（须仅一块）")
    orphan_comments = [
        ln for ln in css.splitlines()
        if "/* THEME:pipeline" in ln and "auto-synced" not in ln
    ]
    if orphan_comments:
        issues.append("preview: global.css 存在游离 THEME:pipeline 注释")
    path = preview_approved_colors_path(project)
    if not path.is_file():
        return issues
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return issues
    light = data.get("light") if isinstance(data, dict) else {}
    expected = str((light or {}).get("primary", "")).upper()
    if not expected:
        return issues
    prefix = resolve_prefix(project).lower()
    m = re.search(rf"--{re.escape(prefix)}-primary:\s*(#[0-9A-Fa-f]{{3,8}})", css, re.I)
    if not m:
        issues.append(f"preview: global.css 缺少 --{prefix}-primary")
        return issues
    actual = m.group(1).upper()
    if actual != expected:
        issues.append(
            f"preview: global.css --{prefix}-primary={actual} 与 preview-approved {expected} 漂移"
        )
    return issues


def _find_tab_root_view(project: Path, page_type: str) -> Path | None:
    src = h5_src_dir(project)
    names = {
        "hub": ("HubView.vue", "HomeView.vue", "PrepareView.vue"),
        "list": ("ListView.vue", "RunsView.vue", "CompareView.vue"),
        "settings": ("SettingsView.vue", "MoreView.vue"),
    }
    views = src / "views"
    if not views.is_dir():
        return None
    for name in names.get(page_type, ()):
        path = views / name
        if path.is_file():
            return path
    return None


def is_view_preview_locked(project: Path, view_path: Path, page_type: str) -> bool:
    if not view_path.is_file():
        return False
    text = view_path.read_text(encoding="utf-8", errors="ignore")
    if PREVIEW_IMPL_LOCK in text:
        return True
    if not has_preview_artifacts(project):
        return False
    markers = TAB_ROOT_MARKERS.get(page_type, ())
    if not markers:
        return False
    hits = sum(1 for m in markers if m in text)
    return hits >= max(3, int(len(markers) * 0.6))


def verify_preview_tab_root_fidelity(project: Path) -> list[str]:
    issues: list[str] = []
    if not is_h5_vite_project(project) or not has_preview_artifacts(project):
        return issues
    prefix = resolve_prefix(project).lower()
    css = ""
    css_path = project / "h5" / "src" / "styles" / "global.css"
    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8", errors="ignore")
    tabbar_cls = f"c-{prefix}-tabbar"
    if tabbar_cls not in css and f"--{prefix}-pill-bg" not in css:
        issues.append(f"preview: TabBar 须为浮动 pill（global.css 缺 {tabbar_cls} 或 --{prefix}-pill-bg）")
    for page_type, markers in TAB_ROOT_MARKERS.items():
        view = _find_tab_root_view(project, page_type)
        if view is None:
            continue
        text = view.read_text(encoding="utf-8", errors="ignore")
        if PREVIEW_IMPL_LOCK not in text:
            issues.append(
                f"preview: {view.name} 首行须含 `{PREVIEW_IMPL_LOCK}`（build.agent 预览实现锁）"
            )
        missing = [m for m in markers if m not in text]
        if len(missing) > len(markers) // 2:
            issues.append(
                f"preview: {view.name} 缺预览结构 marker: {', '.join(missing[:4])}"
            )
    return issues


def verify_preview_hub_data_contract(project: Path) -> list[str]:
    issues: list[str] = []
    if not has_preview_artifacts(project):
        return issues
    hub = _find_tab_root_view(project, "hub")
    if hub is None:
        return issues
    text = hub.read_text(encoding="utf-8", errors="ignore")
    if _KPI_MAGIC_RE.search(text):
        issues.append("preview: HubView 禁止使用 || 8/240 等魔法数占位 KPI")
    if "loadSeason" in text and "deriveHubKpis" not in text:
        issues.append("preview: HubView KPI 须用 deriveHubKpis(finishedRuns)，非 loadSeason 默认 0")
    if "deriveHubKpis" not in text and "finishedRuns" not in text:
        issues.append("preview: HubView 须从 runs 聚合 KPI（deriveHubKpis 或 finishedRuns）")
    seed = h5_src_dir(project) / "store" / "defaultSeed.ts"
    if seed.is_file():
        seed_text = seed.read_text(encoding="utf-8", errors="ignore")
        if "buildDefaultRuns" in seed_text and seed_text.count("planId:") < 1:
            issues.append("preview: buildDefaultRuns() 须含 planId 字段")
    main = h5_src_dir(project) / "main.ts"
    app = h5_src_dir(project) / "App.vue"
    bootstrap = ""
    if main.is_file():
        bootstrap += main.read_text(encoding="utf-8", errors="ignore")
    if app.is_file():
        bootstrap += app.read_text(encoding="utf-8", errors="ignore")
    welcome_logic = h5_src_dir(project) / "views" / "WelcomeView.logic.ts"
    if welcome_logic.is_file():
        bootstrap += welcome_logic.read_text(encoding="utf-8", errors="ignore")
    if "ensureBootstrapData" not in bootstrap:
        issues.append(
            "preview: main.ts / App.vue / WelcomeView.logic 须调用 ensureBootstrapData()"
        )
    return issues


def collect_preview_fidelity_violations(project: Path, app_name: str = "") -> list[str]:
    """Hard gate checks when preview.tabs artifacts exist."""
    project = project.expanduser().resolve()
    if not has_preview_artifacts(project, app_name):
        return []
    issues: list[str] = []
    issues.extend(verify_preview_approved_colors(project, app_name))
    issues.extend(verify_preview_tab_root_fidelity(project))
    issues.extend(verify_preview_hub_data_contract(project))
    return issues
