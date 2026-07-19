"""Tab-root IA blueprint metadata — gate/docs only; no Vue/CSS fragment composer."""

from __future__ import annotations

from batch.skill_pages import H5_PAGE_SPECS

# Canonical section order per tab-root page type (maps to H5_PAGE_SPECS layout intent).
# Hub sections are a superset; topology trims via TOPOLOGY_EXCLUDE / TOPOLOGY_HUB_SECTIONS.
TAB_ROOT_BLUEPRINT: dict[str, tuple[str, ...]] = {
    "hub": (
        "hub-hero",
        "primary-zone",
        "kpi-strip-hub",
        "wizard-lane",
        "chip-rail-hub",
        "feature-bento",
        "cta-stack-hub",
        "draft-list",
        "contextual-feed",
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

# Per-topology hub section sets — product-bound, not one chip dashboard for all.
TOPOLOGY_HUB_SECTIONS: dict[str, tuple[str, ...]] = {
    "T1_dashboard": (
        "hub-hero",
        "kpi-strip-hub",
        "feature-bento",
        "cta-stack-hub",
        "contextual-feed",
    ),
    "T2_capture_first": (
        "hub-hero",
        "primary-zone",
        "cta-stack-hub",
        "contextual-feed",
    ),
    "T3_timeline": (
        "hub-hero",
        "primary-zone",
        "contextual-feed",
        "cta-stack-hub",
    ),
    "T4_wizard": (
        "hub-hero",
        "wizard-lane",
        "draft-list",
        "cta-stack-hub",
    ),
    "T5_workspace": (
        "hub-hero",
        "primary-zone",
        "cta-stack-hub",
        "contextual-feed",
    ),
    "T6_checklist_session": (
        "hub-hero",
        "primary-zone",
        "cta-stack-hub",
        "contextual-feed",
    ),
    "T7_compare_board": (
        "hub-hero",
        "primary-zone",
        "cta-stack-hub",
    ),
    "T8_reminder_ring": (
        "hub-hero",
        "primary-zone",
        "contextual-feed",
        "cta-stack-hub",
    ),
}

TOPOLOGY_EXCLUDE: dict[tuple[str, str], frozenset[str]] = {
    ("hub", "default"): frozenset({"wizard-lane"}),
}

SPEC_REQUIRED_MARKERS: dict[str, tuple[str, ...]] = {
    "hub": ("primary-zone", "empty-state", "cta-primary"),
    "list": ("list-hero", "filter-chips", "list-toolbar", "empty-state", "run-card"),
    "settings": (
        "settings-top",
        "settings-hero",
        "settings-wallet",
        "settings-menu",
        "settings-version",
    ),
}


def resolve_tab_root_sections(page_type: str, topology: str) -> tuple[str, ...]:
    if page_type == "hub" and topology in TOPOLOGY_HUB_SECTIONS:
        return TOPOLOGY_HUB_SECTIONS[topology]
    base = TAB_ROOT_BLUEPRINT.get(page_type, ())
    excluded = TOPOLOGY_EXCLUDE.get((page_type, topology), frozenset())
    return tuple(s for s in base if s not in excluded)


def union_sections_for_targets(
    page_types: tuple[str, ...],
    topology: str,
) -> tuple[str, ...]:
    seen: list[str] = []
    for page_type in page_types:
        for section_id in resolve_tab_root_sections(page_type, topology):
            if section_id not in seen:
                seen.append(section_id)
    return tuple(seen)


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
        if page_type not in TAB_ROOT_BLUEPRINT:
            issues.append(f"blueprint: SPEC_REQUIRED_MARKERS[{page_type}] without TAB_ROOT_BLUEPRINT")
            continue
        if not markers:
            issues.append(f"blueprint: SPEC_REQUIRED_MARKERS[{page_type}] is empty")
    for topo_id, sections in TOPOLOGY_HUB_SECTIONS.items():
        if not sections:
            issues.append(f"blueprint: TOPOLOGY_HUB_SECTIONS[{topo_id}] is empty")
        if "primary-zone" not in sections and "kpi-strip-hub" not in sections and "wizard-lane" not in sections:
            issues.append(
                f"blueprint: TOPOLOGY_HUB_SECTIONS[{topo_id}] missing a primary surface"
            )
    return issues
