"""Parse PM Screen Inventory from 功能文档.md — authoritative H5 route list."""

from __future__ import annotations

import re
from pathlib import Path

SPEC_FILE = "功能文档.md"

_ROUTE_FROM_SCREEN: tuple[tuple[str, str], ...] = (
    ("splash", "/splash"),
    ("welcome gate", "/welcome"),
    ("welcome", "/welcome"),
    ("legal modal", "/legal"),
    ("legal overlay", "/legal"),
    ("legal", "/legal"),
    ("bridge plaza", "/plaza"),
    ("plaza", "/plaza"),
    ("coin store", "/store"),
    ("gem store", "/store"),
    ("iap store", "/store"),
    ("store", "/store"),
)

_NATIVE_ROW_MARKERS = frozenset({"—", "-", "n/a", "na", ""})


def normalize_h5_route(raw: str) -> str | None:
    """Normalize `#/welcome`, `/welcome`, `welcome` → `/welcome`."""
    text = (raw or "").strip()
    if not text or text.lower() in _NATIVE_ROW_MARKERS:
        return None
    m = re.search(r"#(/[\w/:.-]+)", text)
    if m:
        route = m.group(1).rstrip("/") or "/"
        return route if route.startswith("/") else f"/{route}"
    if text.startswith("/"):
        route = text.split("?", 1)[0].rstrip("/") or "/"
        return route
    if re.fullmatch(r"[\w/:.-]+", text):
        return f"/{text.lstrip('/')}"
    return None


def _route_from_screen_name(name: str) -> str | None:
    lower = (name or "").strip().lower()
    if not lower:
        return None
    for needle, route in _ROUTE_FROM_SCREEN:
        if needle in lower:
            return route
    return None


def parse_h5_routes(spec_text: str) -> frozenset[str]:
    """Extract H5 hash routes declared in Screen Inventory."""
    match = re.search(
        r"(?is)(?:^|\n)#+\s*.*screen\s+inventory.*?\n(.*?)(?:\n#+\s|\Z)",
        spec_text,
    )
    if not match:
        return frozenset()

    routes: set[str] = set()
    for line in match.group(1).splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        if re.match(r"^:?-+:?$", cells[0]):
            continue
        header = cells[0].lower()
        if header in ("route", "screen", "name", "screen name", "屏", "屏幕"):
            continue

        route_cell = cells[0]
        screen_cell = cells[1] if len(cells) > 1 else ""
        layer_cell = (cells[2] if len(cells) > 2 else "").lower()

        if layer_cell and "shell" in layer_cell and "h5" not in layer_cell:
            continue

        route = normalize_h5_route(route_cell)
        if route is None:
            route = _route_from_screen_name(screen_cell)
        if route:
            routes.add(route)

    return frozenset(routes)


def read_spec_text(project: Path) -> str:
    path = project / SPEC_FILE
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_project_h5_routes(project: Path) -> frozenset[str]:
    return parse_h5_routes(read_spec_text(project))


def project_includes_route(project: Path, route: str) -> bool:
    normalized = normalize_h5_route(route)
    if not normalized:
        return False
    return normalized in read_project_h5_routes(project)


def ambient_scene_min_rows(routes: frozenset[str]) -> int:
    """Scene map row minimum scales with PM inventory size."""
    if not routes:
        return 2
    return min(4, max(2, len(routes)))


def optional_blueprint_sections(routes: frozenset[str]) -> dict[str, str]:
    """Blueprint V2 sections gated by Screen Inventory routes."""
    return {
        "Welcome Gate Canon": "/welcome",
        "IAP Store Layout": "/store",
    }


def filter_blueprint_v2_sections(
    sections: tuple[str, ...],
    routes: frozenset[str],
) -> tuple[str, ...]:
    gates = optional_blueprint_sections(routes)
    out: list[str] = []
    for section in sections:
        required_route = gates.get(section)
        if required_route and required_route not in routes:
            continue
        out.append(section)
    return tuple(out)


def filter_visual_lock_v2_keys(
    keys: tuple[str, ...],
    routes: frozenset[str],
) -> tuple[str, ...]:
    if "/welcome" in routes:
        return keys
    return tuple(k for k in keys if k != "welcomeSpec")


# --- design-system page slug mapping (skill.pages) ---

_ROUTE_PAGE_SLUG: dict[str, str] = {
    "/splash": "splash",
    "/welcome": "welcome",
    "/hub": "hub",
    "/home": "hub",
    "/prepare": "hub",
    "/runs": "list",
    "/list": "list",
    "/history": "list",
    "/store": "store",
    "/export": "export",
    "/plaza": "plaza",
    "/settings": "settings",
    "/legal": "legal",
    "/live": "live",
}


def _slugify_page_token(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return slug or "screen"


def route_to_page_slug(route: str) -> str:
    """Map Screen Inventory hash route → design-system/pages/{slug}.md stem."""
    normalized = normalize_h5_route(route)
    if not normalized:
        return _slugify_page_token(route)

    base = normalized.split(":", 1)[0].rstrip("/") or "/"
    if base in _ROUTE_PAGE_SLUG:
        return _ROUTE_PAGE_SLUG[base]

    if base.startswith("/wizard") or "/wizard/" in base:
        return "wizard"

    if base.startswith("/run"):
        return "detail"

    if base.startswith("/live"):
        return "live"

    segment = base.strip("/").split("/")[-1]
    if segment and not segment.startswith(":"):
        mapped = _ROUTE_PAGE_SLUG.get(f"/{segment}")
        if mapped:
            return mapped
        return _slugify_page_token(segment)

    return _slugify_page_token(base.replace("/", "-"))


def parse_h5_route_list(spec_text: str) -> list[str]:
    """Ordered H5 routes from Screen Inventory table (deduped, stable order)."""
    match = re.search(
        r"(?is)(?:^|\n)#+\s*.*screen\s+inventory.*?\n(.*?)(?:\n#+\s|\Z)",
        spec_text,
    )
    if not match:
        return []

    routes: list[str] = []
    seen: set[str] = set()
    for line in match.group(1).splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        if re.match(r"^:?-+:?$", cells[0]):
            continue
        header = cells[0].lower()
        if header in ("route", "screen", "name", "screen name", "屏", "屏幕"):
            continue

        route_cell = cells[0]
        screen_cell = cells[1] if len(cells) > 1 else ""
        layer_cell = ""
        purpose_cell = ""
        if len(cells) >= 3:
            if cells[1].lower() in ("h5", "h5 tab", "h5 overlay", "h5 hidden"):
                layer_cell = cells[1].lower()
                purpose_cell = cells[2] if len(cells) > 2 else ""
            else:
                screen_cell = cells[1]
                layer_cell = (cells[2] if len(cells) > 2 else "").lower()
                purpose_cell = cells[3] if len(cells) > 3 else ""

        if layer_cell and "shell" in layer_cell and "h5" not in layer_cell:
            continue
        if route_cell.lower().startswith("native "):
            continue

        route = normalize_h5_route(route_cell)
        if route is None:
            route = _route_from_screen_name(screen_cell)
        if not route or route in seen:
            continue
        seen.add(route)
        routes.append(route)
    return routes


def page_slugs_from_spec(spec_text: str) -> list[str]:
    """Ordered unique design-system page slugs derived from Screen Inventory."""
    slugs: list[str] = []
    seen: set[str] = set()
    for route in parse_h5_route_list(spec_text):
        slug = route_to_page_slug(route)
        if slug in seen:
            continue
        seen.add(slug)
        slugs.append(slug)
    return slugs


def page_slugs_from_project(project: Path) -> list[str]:
    return page_slugs_from_spec(read_spec_text(project))

