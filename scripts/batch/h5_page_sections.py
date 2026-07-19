"""Tab-root IA blueprint metadata — gate/docs only; no Vue/CSS fragment composer."""

from __future__ import annotations

from batch.skill_pages import H5_PAGE_SPECS

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

TOPOLOGY_EXCLUDE: dict[tuple[str, str], frozenset[str]] = {
    ("hub", "default"): frozenset({"wizard-lane"}),
}

SPEC_REQUIRED_MARKERS: dict[str, tuple[str, ...]] = {
    "hub": ("kpi-strip", "chip-rail", "empty-state", "cta-primary"),
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
    return issues
