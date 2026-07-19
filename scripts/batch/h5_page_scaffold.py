"""H5 page helpers — router discovery + bootstrap sync (no page Vue/CSS templates)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from batch.h5_vite_gate import h5_src_dir, is_h5_vite_project

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


def sync_h5_page_scaffold(
    project: Path,
    *,
    app_name: str = "",
    write: bool = True,
) -> list[Path]:
    """Bootstrap-only sync at dev.h5.build — no page Vue/CSS templates."""
    project = project.expanduser().resolve()
    if not is_h5_vite_project(project):
        return []

    if not app_name:
        app_name = project.name

    from batch.h5_default_seed import (
        sync_default_seed_stub,
        sync_main_bootstrap,
        sync_settings_clear_bootstrap,
    )

    written: list[Path] = []
    stub = sync_default_seed_stub(project, app_name=app_name, write=write)
    if stub is not None:
        written.append(stub)
    main_boot = sync_main_bootstrap(project, write=write)
    if main_boot is not None:
        written.append(main_boot)
    settings_logic = sync_settings_clear_bootstrap(project, app_name=app_name, write=write)
    if settings_logic is not None:
        written.append(settings_logic)
    return written


def format_page_scaffold_prompt_block(workspace: Path, app_name: str) -> str:
    from batch.h5_page_prompts import format_page_implementation_prompt_block

    return format_page_implementation_prompt_block(workspace, app_name)
