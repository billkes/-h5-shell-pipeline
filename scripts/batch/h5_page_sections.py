"""Spec-driven tab-root section composer (aligned with skill_pages.H5_PAGE_SPECS)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from batch.h5_vite_scaffold import substitute_text
from batch.skill_pages import H5_PAGE_SPECS

TEMPLATE_ROOT = (
    Path(__file__).resolve().parents[2] / "data" / "static" / "templates" / "h5_vite"
)
SECTIONS_ROOT = TEMPLATE_ROOT / "sections"

SCAFFOLD_START = "<!-- SCAFFOLD:pipeline:start — sync_h5_page_scaffold; do not hand-edit template -->"
SCAFFOLD_END = "<!-- SCAFFOLD:pipeline:end -->"

# Canonical section order per tab-root page type (maps to H5_PAGE_SPECS layout intent).
TAB_ROOT_BLUEPRINT: dict[str, tuple[str, ...]] = {
    "hub": (
        "hub-hero",
        "kpi-strip-hub",
        "wizard-lane",
        "chip-rail-hub",
        "feature-bento",
        "cta-stack-hub",
        "draft-list",
    ),
    "list": (
        "list-hero",
        "kpi-strip-list",
        "chip-rail-list",
        "list-toolbar",
        "list-body",
    ),
    "settings": (
        "settings-hero",
        "settings-wallet",
        "settings-menu",
        "settings-version",
        "settings-clear-dialog",
    ),
}

# Topology trims optional wizard affordances on non-pipeline topologies.
TOPOLOGY_EXCLUDE: dict[tuple[str, str], frozenset[str]] = {
    ("hub", "default"): frozenset({"wizard-lane"}),
}

# Sections rendered after TabBar (modals / veils).
OVERLAY_SECTIONS: frozenset[str] = frozenset({"settings-clear-dialog"})

# CSS fragments emitted when a section is included (shared chunks deduped by order).
SECTION_CSS_FRAGMENTS: dict[str, tuple[str, ...]] = {
    "hub-hero": ("hub-hero.css.frag",),
    "list-hero": ("list-hero.css.frag",),
    "settings-hero": ("settings-hero.css.frag",),
    "kpi-strip-hub": ("kpi-strip.css.frag",),
    "kpi-strip-list": ("kpi-strip.css.frag",),
    "wizard-lane": ("wizard-lane.css.frag",),
    "chip-rail-hub": ("chip-rail.css.frag",),
    "chip-rail-list": ("chip-rail.css.frag",),
    "feature-bento": ("feature-bento.css.frag",),
    "cta-stack-hub": ("cta-stack.css.frag",),
    "draft-list": ("draft-list.css.frag",),
    "list-toolbar": ("list-toolbar.css.frag",),
    "list-body": ("list-body.css.frag",),
    "settings-wallet": ("settings-wallet.css.frag",),
    "settings-menu": ("settings-menu.css.frag",),
    "settings-version": ("settings-version.css.frag",),
}

SPEC_REQUIRED_MARKERS: dict[str, tuple[str, ...]] = {
    "hub": ("kpi-strip", "chip-rail", "empty-state", "cta-primary"),
    "list": ("list-hero", "filter-chips", "list-toolbar", "empty-state", "run-card"),
    "settings": ("settings-hero", "settings-wallet", "settings-menu"),
}


@dataclass(frozen=True)
class TabRootComposePlan:
    page_type: str
    topology: str
    sections: tuple[str, ...]


def resolve_tab_root_sections(page_type: str, topology: str) -> tuple[str, ...]:
    base = TAB_ROOT_BLUEPRINT.get(page_type, ())
    exclude = TOPOLOGY_EXCLUDE.get((page_type, topology), frozenset())
    return tuple(s for s in base if s not in exclude)


def plan_tab_root(page_type: str, topology: str) -> TabRootComposePlan:
    return TabRootComposePlan(
        page_type=page_type,
        topology=topology,
        sections=resolve_tab_root_sections(page_type, topology),
    )


def _read_frag(kind: str, name: str) -> str:
    path = SECTIONS_ROOT / kind / name
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _render_section(section_id: str, values: dict[str, str]) -> str:
    body = _read_frag("vue", f"{section_id}.vue.frag")
    if not body.strip():
        return ""
    return substitute_text(body, values)


def _render_script(page_type: str, values: dict[str, str]) -> str:
    body = _read_frag("scripts", f"{page_type}.script.tpl")
    if not body.strip():
        return ""
    return substitute_text(body, values)


def compose_tab_root_vue(
    page_type: str,
    topology: str,
    *,
    values: dict[str, str],
    title_key: str,
) -> str:
    plan = plan_tab_root(page_type, topology)
    body_parts: list[str] = []
    overlay_parts: list[str] = []
    for section_id in plan.sections:
        chunk = _render_section(section_id, values)
        if not chunk.strip():
            continue
        if section_id in OVERLAY_SECTIONS:
            overlay_parts.append(chunk)
        else:
            body_parts.append(chunk)

    title = values.get(f"{{{{{title_key}}}}}", "")
    shell = _read_frag("shell", "tab-root.shell.tpl")
    if not shell.strip():
        return ""

    inner = "\n\n      ".join(body_parts)
    overlay = "\n    ".join(overlay_parts)
    rendered = substitute_text(
        shell,
        {
            **values,
            "{{PAGE_TITLE}}": title,
            "{{BODY_SECTIONS}}": inner,
            "{{OVERLAY_SECTIONS}}": overlay,
        },
    )
    script = _render_script(page_type, values)
    return f"{SCAFFOLD_START}\n{rendered}\n{SCAFFOLD_END}\n{script}"


def collect_css_fragments(section_ids: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for section_id in section_ids:
        for frag in SECTION_CSS_FRAGMENTS.get(section_id, ()):
            if frag in seen:
                continue
            seen.add(frag)
            ordered.append(frag)
    return tuple(ordered)


def compose_page_scaffold_css(section_ids: tuple[str, ...], *, prefix: str) -> str:
    css_start = "/* PAGE-SCAFFOLD:pipeline — auto-synced; do not hand-edit */"
    css_end = "/* PAGE-SCAFFOLD:end */"
    chunks: list[str] = [css_start]
    for frag in collect_css_fragments(section_ids):
        raw = _read_frag("css", frag)
        if raw.strip():
            chunks.append(substitute_text(raw, {"{{PREFIX}}": prefix}))
    chunks.append(css_end)
    return "\n".join(chunks) + "\n"


def union_sections_for_targets(page_types: tuple[str, ...], topology: str) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for page_type in page_types:
        for section_id in resolve_tab_root_sections(page_type, topology):
            if section_id in seen:
                continue
            seen.add(section_id)
            ordered.append(section_id)
    return tuple(ordered)


def verify_tab_root_blueprint() -> list[str]:
    """CI guard: every tab-root in H5_PAGE_SPECS has a blueprint + required landmarks."""
    issues: list[str] = []
    for page_type in ("hub", "list", "settings"):
        if page_type not in H5_PAGE_SPECS:
            issues.append(f"blueprint: H5_PAGE_SPECS missing {page_type}")
        if page_type not in TAB_ROOT_BLUEPRINT:
            issues.append(f"blueprint: TAB_ROOT_BLUEPRINT missing {page_type}")
            continue
        if not TAB_ROOT_BLUEPRINT[page_type]:
            issues.append(f"blueprint: TAB_ROOT_BLUEPRINT[{page_type}] is empty")
    for page_type, markers in SPEC_REQUIRED_MARKERS.items():
        vue = compose_tab_root_vue(
            page_type,
            "T4_wizard",
            values={
                "{{PREFIX}}": "demo",
                "{{VIEW_STEM}}": "DemoView",
                "{{HUB_TITLE}}": "Prepare",
                "{{LIST_TITLE}}": "Runs",
                "{{SETTINGS_TITLE}}": "Settings",
                "{{HERO_EYEBROW}}": "e",
                "{{HERO_TITLE}}": "t",
                "{{HERO_SUB}}": "s",
                "{{LIST_EYEBROW}}": "e",
                "{{LIST_HEADLINE}}": "t",
                "{{LIST_SUB}}": "s",
                "{{SETTINGS_EYEBROW}}": "e",
                "{{SETTINGS_HEADLINE}}": "t",
                "{{SETTINGS_SUB}}": "s",
            },
            title_key={"hub": "HUB_TITLE", "list": "LIST_TITLE", "settings": "SETTINGS_TITLE"}[
                page_type
            ],
        )
        for marker in markers:
            if marker not in vue:
                issues.append(
                    f"blueprint: {page_type} composed vue missing landmark/marker {marker!r}"
                )
        for section_id in TAB_ROOT_BLUEPRINT[page_type]:
            frag = SECTIONS_ROOT / "vue" / f"{section_id}.vue.frag"
            if not frag.is_file():
                issues.append(f"blueprint: missing section fragment {frag.name}")
    return issues
