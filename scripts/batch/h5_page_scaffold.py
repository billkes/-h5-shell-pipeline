"""Sync tab-root H5 page scaffolds from topology templates (preview-level IA, no review gate)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from batch.h5_theme_tokens import resolve_prefix
from batch.h5_vite_gate import h5_src_dir, is_h5_vite_project
from batch.h5_vite_scaffold import substitute_text, template_values

TEMPLATE_ROOT = (
    Path(__file__).resolve().parents[2] / "data" / "static" / "templates" / "h5_vite"
)

SCAFFOLD_START = "<!-- SCAFFOLD:pipeline:start"
SCAFFOLD_END = "<!-- SCAFFOLD:pipeline:end -->"
CSS_START = "/* PAGE-SCAFFOLD:pipeline — auto-synced; do not hand-edit */"
CSS_END = "/* PAGE-SCAFFOLD:end */"

PAGE_TYPE_TITLES: dict[str, tuple[str, str]] = {
    "hub": ("Prepare", "HUB_TITLE"),
    "list": ("Runs", "LIST_TITLE"),
    "settings": ("Settings", "SETTINGS_TITLE"),
}

_ROUTE_PAGE_TYPE: tuple[tuple[str, str], ...] = (
    ("/hub", "hub"),
    ("/home", "hub"),
    ("/prepare", "hub"),
    ("/list", "list"),
    ("/runs", "list"),
    ("/settings", "settings"),
)

_SEGMENT_PAGE_TYPE: dict[str, str] = {
    "hub": "hub",
    "home": "hub",
    "prepare": "hub",
    "list": "list",
    "runs": "list",
    "settings": "settings",
}


def route_to_page_type(route: str) -> str | None:
    text = (route or "").strip()
    if text.startswith("#"):
        text = text[1:]
    normalized = text.split("?", 1)[0].rstrip("/") or "/"
    lower = normalized.lower()
    for path, page_type in _ROUTE_PAGE_TYPE:
        if lower == path:
            return page_type
    segment = lower.rsplit("/", 1)[-1]
    return _SEGMENT_PAGE_TYPE.get(segment)

TOPOLOGY_PAGE_TEMPLATE: dict[tuple[str, str], str] = {
    ("hub", "T4_wizard"): "hub.T4_wizard.vue.tpl",
    ("hub", "default"): "hub.T4_wizard.vue.tpl",
    ("list", "T4_wizard"): "list.T4_wizard.vue.tpl",
    ("list", "default"): "list.T4_wizard.vue.tpl",
    ("settings", "default"): "settings.default.vue.tpl",
    ("settings", "T4_wizard"): "settings.default.vue.tpl",
}


@dataclass(frozen=True)
class ScaffoldTarget:
    page_type: str
    route: str
    view_path: Path
    view_stem: str


def resolve_topology(project: Path) -> str:
    for rel in ("skill-input/context.json",):
        path = project / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            tid = str((data.get("constraints") or {}).get("interactionTopology") or "").strip()
            if tid:
                return tid
    lock = project / "本包维度锁.json"
    if lock.is_file():
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
            tid = str(data.get("interactionTopology") or "").strip()
            if tid:
                return tid
        except json.JSONDecodeError:
            pass
    return "default"


def _parse_router_views(router_text: str) -> list[tuple[str, str, str]]:
    """Return (route, component_name, vue_relative_path)."""
    import_map: dict[str, str] = {}
    for m in re.finditer(
        r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+\.vue)[\'"]',
        router_text,
    ):
        import_map[m.group(1)] = m.group(2)

    out: list[tuple[str, str, str]] = []
    for block in re.finditer(r"\{([^{}]*path\s*:[^{}]*)\}", router_text, re.S):
        chunk = block.group(1)
        path_m = re.search(r"path\s*:\s*['\"]([^'\"]+)['\"]", chunk)
        if not path_m:
            continue
        route = path_m.group(1).split(":", 1)[0]
        comp_m = re.search(r"component\s*:\s*(\w+)", chunk)
        if not comp_m:
            continue
        comp = comp_m.group(1)
        rel = import_map.get(comp, f"../views/{comp}.vue")
        out.append((route, comp, rel))
    return out


def _discover_scaffold_targets(project: Path) -> list[ScaffoldTarget]:
    src = h5_src_dir(project)
    router = src / "router" / "index.ts"
    if not router.is_file():
        return []
    routes = _parse_router_views(router.read_text(encoding="utf-8", errors="ignore"))
    targets: list[ScaffoldTarget] = []
    seen: set[str] = set()
    for route, _comp, rel in routes:
        page_type = route_to_page_type(route)
        if not page_type or page_type not in PAGE_TYPE_TITLES:
            continue
        vue_path = (src / rel.replace("../", "")).resolve()
        if not vue_path.is_file():
            vue_path = src / "views" / Path(rel).name
        if not vue_path.is_file():
            continue
        key = f"{page_type}:{vue_path.name}"
        if key in seen:
            continue
        seen.add(key)
        targets.append(
            ScaffoldTarget(
                page_type=page_type,
                route=route,
                view_path=vue_path,
                view_stem=vue_path.stem,
            )
        )
    return targets


def _hero_copy(project: Path) -> dict[str, str]:
    eyebrow = "Timed Rehearsal Coach"
    title = "Map your script to the clock"
    sub = "Import, time-map sections, rehearse with live pace monitoring — all on-device."
    ctx = project / "skill-input" / "context.json"
    if ctx.is_file():
        try:
            data = json.loads(ctx.read_text(encoding="utf-8"))
            product = data.get("product") or {}
            if product.get("localFeature"):
                eyebrow = str(product.get("coreScene") or eyebrow)[:48]
            flow = str(product.get("themeAngle") or "")
            if "presentation" in flow.lower() or "speech" in flow.lower():
                sub = (
                    "Import, time-map sections, rehearse with live pace monitoring — all on-device."
                )
        except json.JSONDecodeError:
            pass
    return {
        "{{HERO_EYEBROW}}": eyebrow,
        "{{HERO_TITLE}}": title,
        "{{HERO_SUB}}": sub,
    }


def _template_name(page_type: str, topology: str) -> str | None:
    return TOPOLOGY_PAGE_TEMPLATE.get((page_type, topology)) or TOPOLOGY_PAGE_TEMPLATE.get(
        (page_type, "default")
    )


def _build_substitutions(
    project: Path,
    *,
    app_name: str,
    prefix: str,
    target: ScaffoldTarget,
) -> dict[str, str]:
    values = template_values(project, app_name=app_name, prefix=prefix)
    values["{{VIEW_STEM}}"] = target.view_stem
    title, title_key = PAGE_TYPE_TITLES[target.page_type]
    values["{{" + title_key + "}}"] = title
    if target.page_type == "hub":
        values.update(_hero_copy(project))
    return values


def _render_template(page_type: str, topology: str, values: dict[str, str]) -> str:
    name = _template_name(page_type, topology)
    if not name:
        return ""
    path = TEMPLATE_ROOT / "pages" / name
    if not path.is_file():
        return ""
    return substitute_text(path.read_text(encoding="utf-8"), values)


def _merge_vue_scaffold(existing: str, rendered: str) -> str:
    if SCAFFOLD_START not in rendered:
        return rendered
    start_idx = rendered.find("<!-- SCAFFOLD:pipeline:start")
    end_idx = rendered.find(SCAFFOLD_END)
    if start_idx < 0 or end_idx < 0:
        return rendered
    scaffold_block = rendered[start_idx : end_idx + len(SCAFFOLD_END)]
    script_part = rendered[end_idx + len(SCAFFOLD_END) :].lstrip()

    if SCAFFOLD_START in existing:
        pre = existing.split(SCAFFOLD_START, 1)[0]
        post_tail = existing.split(SCAFFOLD_END, 1)[-1]
        return pre + scaffold_block + post_tail
    return scaffold_block + "\n" + script_part


def _replace_css_block(raw: str, block: str) -> str:
    if CSS_START in raw and CSS_END in raw:
        pre, rest = raw.split(CSS_START, 1)
        _old, post = rest.split(CSS_END, 1)
        return pre + block + post
    return raw.rstrip() + "\n\n" + block + "\n"


def sync_h5_page_scaffold_css(project: Path, *, write: bool = True) -> Path | None:
    if not is_h5_vite_project(project):
        return None
    css_path = h5_src_dir(project) / "styles" / "global.css"
    if not css_path.is_file():
        return None
    prefix = resolve_prefix(project).lower()
    tpl = TEMPLATE_ROOT / "styles" / "page-scaffold.css.tpl"
    if not tpl.is_file():
        return None
    block = substitute_text(tpl.read_text(encoding="utf-8"), {"{{PREFIX}}": prefix})
    raw = css_path.read_text(encoding="utf-8")
    updated = _replace_css_block(raw, block)
    if write and updated != raw:
        css_path.write_text(updated, encoding="utf-8")
    return css_path


def sync_h5_page_scaffold(
    project: Path,
    *,
    app_name: str = "",
    write: bool = True,
) -> list[Path]:
    """Write tab-root Vue scaffolds from topology templates. Logic files are never overwritten."""
    project = project.expanduser().resolve()
    if not is_h5_vite_project(project):
        return []

    if not app_name:
        app_name = project.name
    prefix = resolve_prefix(project)
    topology = resolve_topology(project)
    targets = _discover_scaffold_targets(project)
    written: list[Path] = []

    css_path = sync_h5_page_scaffold_css(project, write=write)
    if css_path is not None:
        written.append(css_path)

    for target in targets:
        values = _build_substitutions(project, app_name=app_name, prefix=prefix, target=target)
        rendered = _render_template(target.page_type, topology, values)
        if not rendered:
            continue
        if write:
            target.view_path.write_text(rendered, encoding="utf-8")
            written.append(target.view_path)

    return written


def format_page_scaffold_prompt_block(workspace: Path, app_name: str) -> str:
    topology = resolve_topology(workspace)
    targets = _discover_scaffold_targets(workspace)
    lines = [
        "[Tab-root Page Scaffold — pipeline-owned; DO NOT rewrite template]",
        f"- Topology: `{topology}` → sync_h5_page_scaffold generates hub/list/settings layout.",
        "- Implement business logic ONLY in `views/*View.logic.ts` (create if missing).",
        "- Wizard / Live / Export / RunDetail — full Agent ownership.",
        "",
    ]
    if targets:
        lines.append("Pipeline-scaffolded views:")
        for t in targets:
            lines.append(f"- `{t.view_path.name}` + `{t.view_stem}.logic.ts` (Agent writes logic only)")
    else:
        lines.append("- Tab-root views will be scaffolded when router declares /hub, /runs, /settings.")
    return "\n".join(lines)
