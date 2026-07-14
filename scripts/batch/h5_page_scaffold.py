"""Sync tab-root H5 page scaffolds from topology templates (preview-level IA, no review gate)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from batch.h5_ui_copy import hero_copy, list_copy, settings_copy, welcome_copy
from batch.h5_legal_ui import project_needs_legal_ui
from batch.h5_theme_tokens import resolve_prefix
from batch.h5_vite_gate import h5_src_dir, is_h5_vite_project
from batch.preview_fidelity_gate import (
    PREVIEW_IMPL_LOCK,
    has_preview_artifacts,
    is_view_preview_locked,
)
from batch.h5_page_sections import (
    compose_page_scaffold_css,
    compose_tab_root_vue,
    union_sections_for_targets,
)
from batch.h5_vite_scaffold import substitute_text, template_values

TEMPLATE_ROOT = (
    Path(__file__).resolve().parents[2] / "data" / "static" / "templates" / "h5_vite"
)

SCAFFOLD_START = "<!-- SCAFFOLD:pipeline:start"
SCAFFOLD_END = "<!-- SCAFFOLD:pipeline:end -->"
CSS_START = "/* PAGE-SCAFFOLD:pipeline — auto-synced; do not hand-edit */"
CSS_END = "/* PAGE-SCAFFOLD:end */"
LEGAL_CSS_START = "/* LEGAL:pipeline — auto-synced; do not hand-edit */"
LEGAL_CSS_END = "/* LEGAL:end */"

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


def _extract_bracket_body(text: str, open_idx: int) -> str | None:
    """Return inner text for `[` or `{` at *open_idx*, or None if unbalanced."""
    if open_idx >= len(text) or text[open_idx] not in "{[":
        return None
    open_ch = text[open_idx]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    for i in range(open_idx, len(text)):
        ch = text[i]
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[open_idx + 1 : i]
    return None


def _routes_array_body(router_text: str) -> str | None:
    for pattern in (r"routes\s*:\s*\[", r"routes\s*=\s*\["):
        match = re.search(pattern, router_text)
        if not match:
            continue
        body = _extract_bracket_body(router_text, match.end() - 1)
        if body is not None:
            return body
    return None


def _iter_route_object_blocks(routes_body: str):
    i = 0
    while i < len(routes_body):
        if routes_body[i] != "{":
            i += 1
            continue
        block = _extract_bracket_body(routes_body, i)
        if block is None:
            break
        full = "{" + block + "}"
        if re.search(r"\bpath\s*:", full) and re.search(r"\bcomponent\s*:", full):
            yield full
        i += len(full)


def _parse_router_views(router_text: str) -> list[tuple[str, str, str]]:
    """Return (route, component_name, vue_relative_path)."""
    import_map: dict[str, str] = {}
    for m in re.finditer(
        r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+\.vue)[\'"]',
        router_text,
    ):
        import_map[m.group(1)] = m.group(2)

    routes_body = _routes_array_body(router_text) or router_text
    out: list[tuple[str, str, str]] = []
    for chunk in _iter_route_object_blocks(routes_body):
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
        vue_path = src / "views" / Path(rel).name
        if not vue_path.is_file():
            candidate = (src / rel.replace("../", "")).resolve()
            if candidate.is_file():
                vue_path = candidate
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
        values.update(hero_copy(project))
    if target.page_type == "list":
        values.update(list_copy(project))
    if target.page_type == "settings":
        values.update(settings_copy(project))
    return values


def _render_tab_root(page_type: str, topology: str, values: dict[str, str]) -> str:
    _title_default, title_key = PAGE_TYPE_TITLES[page_type]
    return compose_tab_root_vue(page_type, topology, values=values, title_key=title_key)


def _merge_vue_scaffold(existing: str, rendered: str, *, replace_script: bool = False) -> str:
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
        if replace_script and script_part:
            post_tail = "\n" + script_part
        return pre + scaffold_block + post_tail
    return scaffold_block + "\n" + script_part


def _replace_css_block(raw: str, block: str) -> str:
    if CSS_START in raw and CSS_END in raw:
        pre, rest = raw.split(CSS_START, 1)
        _old, post = rest.split(CSS_END, 1)
        return pre + block + post
    return raw.rstrip() + "\n\n" + block + "\n"


def _replace_marked_block(raw: str, block: str, *, start: str, end: str) -> str:
    if start in raw and end in raw:
        pre, rest = raw.split(start, 1)
        _old, post = rest.split(end, 1)
        return pre + block + post
    return raw.rstrip() + "\n\n" + block + "\n"


def _find_welcome_view(project: Path) -> Path | None:
    src = h5_src_dir(project)
    router = src / "router" / "index.ts"
    if not router.is_file():
        return None
    for route, _comp, rel in _parse_router_views(
        router.read_text(encoding="utf-8", errors="ignore")
    ):
        if route.rstrip("/").lower() != "/welcome":
            continue
        vue_path = src / rel.replace("../", "")
        if vue_path.is_file():
            return vue_path
        candidate = src / "views" / Path(rel).name
        return candidate if candidate.is_file() else vue_path
    for path in sorted((src / "views").glob("*elcome*.vue")):
        return path
    return None


def _parse_router_paths(router_text: str) -> list[str]:
    return re.findall(r"path\s*:\s*['\"]([^'\"]+)['\"]", router_text)


def _router_includes_route(project: Path, route: str) -> bool:
    src = h5_src_dir(project)
    router_path = src / "router" / "index.ts"
    if not router_path.is_file():
        return False
    want = (route or "").split("?", 1)[0].rstrip("/").lower() or "/"
    for path in _parse_router_paths(router_path.read_text(encoding="utf-8", errors="ignore")):
        got = path.rstrip("/").lower() or "/"
        if got == want:
            return True
    return False


def sync_h5_legal_overlay_css(project: Path, *, write: bool = True) -> Path | None:
    if not is_h5_vite_project(project) or not project_needs_legal_ui(project):
        return None
    css_path = h5_src_dir(project) / "styles" / "global.css"
    if not css_path.is_file():
        return None
    tpl = TEMPLATE_ROOT / "styles" / "legal-overlay.css.tpl"
    if not tpl.is_file():
        return None
    prefix = resolve_prefix(project).lower()
    block = substitute_text(tpl.read_text(encoding="utf-8"), {"{{PREFIX}}": prefix})
    raw = css_path.read_text(encoding="utf-8")
    updated = _replace_marked_block(
        raw, block, start=LEGAL_CSS_START, end=LEGAL_CSS_END
    )
    if write and updated != raw:
        css_path.write_text(updated, encoding="utf-8")
    return css_path


def sync_h5_legal_overlay_component(project: Path, *, write: bool = True) -> Path | None:
    if not is_h5_vite_project(project) or not project_needs_legal_ui(project):
        return None
    tpl = TEMPLATE_ROOT / "components" / "LegalOverlay.vue.tpl"
    if not tpl.is_file():
        return None
    prefix = resolve_prefix(project).lower()
    rendered = substitute_text(tpl.read_text(encoding="utf-8"), {"{{PREFIX}}": prefix})
    lib_tpl = TEMPLATE_ROOT / "src" / "lib" / "formatLegalBody.ts"
    lib_dest = h5_src_dir(project) / "lib" / "formatLegalBody.ts"
    if lib_tpl.is_file() and write:
        lib_dest.parent.mkdir(parents=True, exist_ok=True)
        lib_dest.write_text(lib_tpl.read_text(encoding="utf-8"), encoding="utf-8")
    for subdir in ("components", "views"):
        dest = h5_src_dir(project) / subdir / "LegalOverlay.vue"
        if dest.is_file() or subdir == "components":
            if write:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(rendered, encoding="utf-8")
            return dest
    return None


def sync_h5_welcome_scaffold(
    project: Path,
    *,
    app_name: str = "",
    write: bool = True,
) -> list[Path]:
    if not is_h5_vite_project(project) or not _router_includes_route(project, "/welcome"):
        return []
    if not app_name:
        app_name = project.name
    prefix = resolve_prefix(project)
    welcome_view = _find_welcome_view(project)
    if welcome_view is None:
        welcome_view = h5_src_dir(project) / "views" / "WelcomeView.vue"
    logic_path = welcome_view.parent / "WelcomeView.logic.ts"
    tpl = TEMPLATE_ROOT / "pages" / "welcome.gate.vue.tpl"
    logic_tpl = TEMPLATE_ROOT / "pages" / "welcome.logic.ts.tpl"
    if not tpl.is_file():
        return []
    values = template_values(project, app_name=app_name, prefix=prefix)
    values.update(welcome_copy(project, app_name=app_name))
    rendered = substitute_text(tpl.read_text(encoding="utf-8"), values)
    written: list[Path] = []
    if write:
        welcome_view.parent.mkdir(parents=True, exist_ok=True)
        existing = welcome_view.read_text(encoding="utf-8") if welcome_view.is_file() else ""
        welcome_view.write_text(
            _merge_vue_scaffold(existing, rendered, replace_script=True),
            encoding="utf-8",
        )
        written.append(welcome_view)
        if logic_tpl.is_file():
            logic_body = substitute_text(logic_tpl.read_text(encoding="utf-8"), values)
            if write:
                logic_path.write_text(logic_body, encoding="utf-8")
                written.append(logic_path)
    return written


def sync_h5_plaza_scaffold(
    project: Path,
    *,
    app_name: str = "",
    write: bool = True,
) -> list[Path]:
    """Canonical Bridge Plaza view; purchase QA SKU fixed to 311400."""
    if not is_h5_vite_project(project) or not _router_includes_route(project, "/plaza"):
        return []
    tpl = TEMPLATE_ROOT / "pages" / "plaza.vue.tpl"
    logic_tpl = TEMPLATE_ROOT / "pages" / "plaza.logic.ts.tpl"
    if not tpl.is_file():
        return []
    from batch.h5_plaza_purchase import find_plaza_view

    plaza_view = find_plaza_view(project)
    if plaza_view is None:
        plaza_view = h5_src_dir(project) / "views" / "PlazaView.vue"
    if not app_name:
        app_name = project.name
    prefix = resolve_prefix(project)
    values = template_values(project, app_name=app_name, prefix=prefix)
    written: list[Path] = []
    if write:
        plaza_view.parent.mkdir(parents=True, exist_ok=True)
        plaza_view.write_text(substitute_text(tpl.read_text(encoding="utf-8"), values), encoding="utf-8")
        written.append(plaza_view)
        if logic_tpl.is_file():
            logic_path = plaza_view.parent / "PlazaView.logic.ts"
            logic_path.write_text(substitute_text(logic_tpl.read_text(encoding="utf-8"), values), encoding="utf-8")
            written.append(logic_path)
    return written


def sync_h5_page_scaffold_css(
    project: Path,
    *,
    page_types: tuple[str, ...] = (),
    topology: str = "default",
    write: bool = True,
) -> Path | None:
    if not is_h5_vite_project(project):
        return None
    if has_preview_artifacts(project):
        return h5_src_dir(project) / "styles" / "global.css"
    css_path = h5_src_dir(project) / "styles" / "global.css"
    if not css_path.is_file():
        return None
    prefix = resolve_prefix(project).lower()
    if not page_types:
        targets = _discover_scaffold_targets(project)
        page_types = tuple(dict.fromkeys(t.page_type for t in targets))
    section_ids = union_sections_for_targets(page_types, topology)
    block = compose_page_scaffold_css(section_ids, prefix=prefix)
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
    page_types = tuple(dict.fromkeys(t.page_type for t in targets))

    css_path = sync_h5_page_scaffold_css(
        project, page_types=page_types, topology=topology, write=write
    )
    if css_path is not None:
        written.append(css_path)

    legal_css = sync_h5_legal_overlay_css(project, write=write)
    if legal_css is not None:
        written.append(legal_css)

    legal_vue = sync_h5_legal_overlay_component(project, write=write)
    if legal_vue is not None:
        written.append(legal_vue)

    written.extend(sync_h5_welcome_scaffold(project, app_name=app_name, write=write))
    written.extend(sync_h5_plaza_scaffold(project, app_name=app_name, write=write))
    from batch.h5_default_seed import (
        sync_default_seed_stub,
        sync_main_bootstrap,
        sync_settings_clear_bootstrap,
    )

    stub = sync_default_seed_stub(project, app_name=app_name, write=write)
    if stub is not None:
        written.append(stub)
    main_boot = sync_main_bootstrap(project, write=write)
    if main_boot is not None:
        written.append(main_boot)
    settings_logic = sync_settings_clear_bootstrap(project, app_name=app_name, write=write)
    if settings_logic is not None:
        written.append(settings_logic)

    for target in targets:
        if is_view_preview_locked(project, target.view_path, target.page_type):
            print(
                f">>> dev.h5.build: skipped page scaffold (preview-locked) → "
                f"{target.view_path.relative_to(project)}"
            )
            continue
        values = _build_substitutions(project, app_name=app_name, prefix=prefix, target=target)
        rendered = _render_tab_root(target.page_type, topology, values)
        if not rendered:
            continue
        if write:
            target.view_path.parent.mkdir(parents=True, exist_ok=True)
            target.view_path.write_text(rendered, encoding="utf-8")
            written.append(target.view_path)

    return written


def format_page_scaffold_prompt_block(workspace: Path, app_name: str) -> str:
    topology = resolve_topology(workspace)
    targets = _discover_scaffold_targets(workspace)
    lines = [
        "[Tab-root Page Scaffold — pipeline-owned; DO NOT rewrite template]",
        f"- Topology: `{topology}` → section composer builds hub/list/settings from `sections/*.vue.frag`.",
        "- Blueprint: `TAB_ROOT_BLUEPRINT` in `h5_page_sections.py` (aligned with `H5_PAGE_SPECS`).",
        "- Implement business logic ONLY in `views/*View.logic.ts` (create if missing).",
        "- Wizard / Live / Export / RunDetail — full Agent ownership.",
        "- Welcome / Legal overlay markup + global CSS are pipeline-owned when legal docs or Legal modal are in scope.",
        "- **All pipeline scaffold copy is English-only** — never inject CSV 中文主题/核心场景 into visible UI.",
        "- When `_preview/*-tabs-preview.html` exists: tab-root views with `"
        + PREVIEW_IMPL_LOCK
        + "` or preview DOM markers are **never overwritten** by this step.",
        "",
    ]
    if targets:
        lines.append("Pipeline-scaffolded views:")
        for t in targets:
            lines.append(f"- `{t.view_path.name}` + `{t.view_stem}.logic.ts` (Agent writes logic only)")
    else:
        lines.append("- Tab-root views will be scaffolded when router declares /hub, /runs, /settings.")
    return "\n".join(lines)
