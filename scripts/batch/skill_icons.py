"""H5 icon sprite helpers — bridge uupm icon briefs to inline SVG kit."""

from __future__ import annotations

import re

CANONICAL_ICON_SLUGS: tuple[str, ...] = (
    "home",
    "list",
    "settings",
    "search",
    "add",
    "edit",
    "delete",
    "export",
    "store",
    "chevron-left",
    "chevron-right",
    "close",
    "check",
    "filter",
    "calendar",
    "user",
    "warn",
    "empty",
    "legal",
    "camera",
    "gallery",
)

SEMANTIC_ALIASES: dict[str, str] = {
    "house": "home",
    "x": "close",
    "pencil-simple": "edit",
    "pencil": "edit",
    "trash": "delete",
    "plus": "add",
    "download-simple": "export",
    "arrow-left": "chevron-left",
    "arrow-right": "chevron-right",
    "caret-down": "chevron-down",
    "caret-up": "chevron-up",
    "magnifying-glass": "search",
    "gear": "settings",
    "gear-six": "settings",
}

FORBIDDEN_ICON_LIBRARIES: tuple[str, ...] = (
    "iconfont",
    "fontawesome",
    "font-awesome",
    "material-icons",
    "material-symbols",
    "phosphor",
    "lucide",
    "heroicons",
    "fa-solid",
    "fa-regular",
)

_ICON_NAME_RE = re.compile(r"^\s*-\s*\*\*Icon Name:\*\*\s*(.+)$", re.I)


def normalize_icon_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return SEMANTIC_ALIASES.get(slug, slug) or "mark"


def h5_symbol_id(prefix: str, slug: str) -> str:
    p = (prefix or "app").strip().lower()
    return f"{p}-mark-{slug}"


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


def format_h5_icon_landing_block(prefix: str) -> str:
    p = (prefix or "app").strip().lower()
    forbidden = " · ".join(f"`{lib}`" for lib in FORBIDDEN_ICON_LIBRARIES[:8])
    return "\n".join(
        [
            "## H5 Delivery Canon (h5-shell-pipeline — MANDATORY)",
            "",
            "Rows above are **semantic reference only**. Ignore `Library` and `Import Code` for H5.",
            "",
            "| Rule | Requirement |",
            "|------|-------------|",
            f"| Delivery | Inline SVG `<symbol>` in `{p}_entry.htm` hidden sprite block |",
            f"| Symbol ID | `{p}-mark-{{slug}}` (e.g. `{p}-mark-home`) |",
            "| Stroke | `currentColor`, stroke-width 1.8–2, viewBox `0 0 24 24` |",
            f"| Forbidden | {forbidden} … |",
            "",
            "Resolved symbol IDs: read `skill-adapt/icon-sprite-manifest.json`.",
            "Cross-pack icon **style is unified** — do not import per-pack icon libraries.",
            "",
        ]
    )
