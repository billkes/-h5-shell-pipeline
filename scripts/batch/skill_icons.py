"""H5 icon helpers — unify on skill ui-ux-pro-max Phosphor catalog."""

from __future__ import annotations

import re

# Semantic slugs aligned with skill icons.csv (Phosphor names normalized).
CANONICAL_ICON_SLUGS: tuple[str, ...] = (
    "house",
    "list",
    "gear",
    "magnifying-glass",
    "plus",
    "pencil-simple",
    "trash",
    "download-simple",
    "storefront",
    "caret-left",
    "caret-right",
    "x",
    "check",
    "funnel",
    "calendar",
    "user",
    "warning",
    "info",
    "camera",
    "image",
)

# Map common aliases → Phosphor icon names from skill icons.csv.
SEMANTIC_ALIASES: dict[str, str] = {
    "home": "house",
    "settings": "gear",
    "gear-six": "gear",
    "search": "magnifying-glass",
    "add": "plus",
    "edit": "pencil-simple",
    "pencil": "pencil-simple",
    "delete": "trash",
    "export": "download-simple",
    "store": "storefront",
    "close": "x",
    "filter": "funnel",
    "warn": "warning",
    "empty": "info",
    "legal": "info",
    "gallery": "image",
    "chevron-left": "caret-left",
    "chevron-right": "caret-right",
    "arrow-left": "caret-left",
    "arrow-right": "caret-right",
}

# Still forbidden — not in skill H5 delivery path.
FORBIDDEN_ICON_LIBRARIES: tuple[str, ...] = (
    "iconfont",
    "fontawesome",
    "font-awesome",
    "material-icons",
    "material-symbols",
    "fa-solid",
    "fa-regular",
    "fa-brands",
)

ALLOWED_ICON_LIBRARY = "Phosphor"
ALLOWED_ICON_PACKAGE = "@phosphor-icons/vue"

_ICON_NAME_RE = re.compile(r"^\s*-\s*\*\*Icon Name:\*\*\s*(.+)$", re.I)


def normalize_icon_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return SEMANTIC_ALIASES.get(slug, slug) or "info"


def h5_symbol_id(prefix: str, slug: str) -> str:
    """Legacy helper — Phosphor uses component names; kept for tests/ledger."""
    p = (prefix or "app").strip().lower()
    return f"{p}-ph-{slug}"


def parse_icon_names_from_brief(text: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = _ICON_NAME_RE.match(line)
        if not match:
            continue
        raw = match.group(1).strip()
        slug = normalize_icon_slug(raw)
        if slug and slug not in seen:
            seen.add(slug)
            names.append(slug)
    return names


def phosphor_component_name(slug: str) -> str:
    """Convert `pencil-simple` → `PencilSimple` for @phosphor-icons/vue."""
    parts = [p for p in normalize_icon_slug(slug).split("-") if p]
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Info"


def format_h5_icon_landing_block(prefix: str) -> str:
    """Canon block appended to skill.enrich icon-brief.md."""
    del prefix  # prefix unused — Phosphor package is global
    forbidden = " · ".join(f"`{lib}`" for lib in FORBIDDEN_ICON_LIBRARIES)
    return "\n".join(
        [
            "## H5 Delivery Canon (h5-shell-pipeline — MANDATORY)",
            "",
            "Rows above are the **skill icon catalog**. Use Library + Import Code.",
            "",
            "| Rule | Requirement |",
            "|------|-------------|",
            f"| Library | **{ALLOWED_ICON_LIBRARY}** only |",
            f"| Package | `{ALLOWED_ICON_PACKAGE}` |",
            "| Import | `import {{ House }} from '@phosphor-icons/vue'` (PascalCase component) |",
            "| Weight | `regular` / `bold` per icon-brief Style |",
            f"| Forbidden | {forbidden} |",
            "",
            "Resolved list: read `skill-adapt/icon-manifest.json`.",
            "Do **not** invent a parallel inline-SVG sprite kit that ignores Phosphor.",
            "",
        ]
    )
