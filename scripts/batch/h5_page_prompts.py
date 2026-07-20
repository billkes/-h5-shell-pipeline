"""Per-app H5 page spec index + front-loaded Welcome/Tab1 Scene Brief for Agent."""

from __future__ import annotations

import re
from pathlib import Path

from batch.h5_legal_ui import project_needs_legal_ui
from batch.h5_page_scaffold import _discover_scaffold_targets, _router_includes_route
from batch.h5_vite_gate import h5_src_dir, is_h5_vite_project
from batch.uupm_design_system import design_system_dir_for_app, master_path_for_app

# Pages whose Scene Brief must be inlined into the Agent front-load (not path-only).
_FRONTLOAD_PAGES: tuple[str, ...] = ("welcome", "hub")

_SCENE_FIELD_RE = re.compile(
    r"^\s*-\s*\*\*(?P<key>[^*]+):\*\*\s*(?P<val>.+?)\s*$",
    re.MULTILINE,
)

_SCENE_KEYS_WELCOME: tuple[str, ...] = (
    "Audience",
    "Core scene",
    "Local feature",
    "Visual motif",
    "Color temperature",
    "Shape language",
    "Flow beats to express",
)

_SCENE_KEYS_HUB: tuple[str, ...] = (
    "Topology",
    "Audience",
    "Core scene",
    "Local feature",
    "Visual motif",
    "Primary zone intent",
    "Feed style",
    "Forbidden landing",
    "Workflow entry hints",
)


def _rel(project: Path, path: Path) -> str:
    try:
        return path.relative_to(project).as_posix()
    except ValueError:
        return str(path)


def _existing(project: Path, rel: str) -> str | None:
    path = project / rel
    return _rel(project, path) if path.is_file() else None


def collect_page_spec_file_index(project: Path, app_name: str) -> dict[str, list[str]]:
    """Return grouped spec paths that exist on disk."""
    project = project.expanduser().resolve()
    out: dict[str, list[str]] = {
        "design_system_pages": [],
        "design_system_root": [],
        "product_locks": [],
        "views": [],
    }

    ds = design_system_dir_for_app(project, app_name)
    master = master_path_for_app(project, app_name)
    if master.is_file():
        out["design_system_root"].append(_rel(project, master))
    for stack_name in (
        "stack-vue.md",
        "stack-html-tailwind.md",
        "h5-runtime.md",
        "ux-checklist.md",
        "icon-brief.md",
    ):
        stack = ds / stack_name
        if stack.is_file():
            out["design_system_root"].append(_rel(project, stack))
    for brief_name in (
        "style-brief.md",
        "typography-brief.md",
        "color-brief.md",
        "motion-brief.md",
        "h5-interface-brief.md",
    ):
        brief = ds / brief_name
        if brief.is_file():
            rel_path = _rel(project, brief)
            if rel_path not in out["design_system_root"]:
                out["design_system_root"].append(rel_path)
    pages_dir = ds / "pages"
    if pages_dir.is_dir():
        for path in sorted(pages_dir.glob("*.md")):
            out["design_system_pages"].append(_rel(project, path))

    for rel in (
        "功能文档.md",
        "视觉蓝图.md",
        "本包视觉锁.json",
        "skill-input/context.json",
        "skill-adapt/kit-skeleton.css",
    ):
        hit = _existing(project, rel)
        if hit:
            out["product_locks"].append(hit)

    if _router_includes_route(project, "/welcome") and not any(
        p.endswith("/pages/welcome.md") for p in out["design_system_pages"]
    ):
        welcome_page = pages_dir / "welcome.md"
        if welcome_page.is_file():
            out["design_system_pages"].append(_rel(project, welcome_page))

    if project_needs_legal_ui(project):
        for pattern in ("* Privacy Agreement.md", "* User Agreement.md"):
            for path in sorted(project.glob(pattern)):
                out["product_locks"].append(_rel(project, path))

    welcome_view = h5_src_dir(project) / "views" / "WelcomeView.vue"
    if welcome_view.is_file():
        out["views"].append(_rel(project, welcome_view))
    for target in _discover_scaffold_targets(project):
        out["views"].append(_rel(project, target.view_path))

    if _router_includes_route(project, "/plaza"):
        plaza = h5_src_dir(project) / "views" / "PlazaView.vue"
        if plaza.is_file():
            rel = _rel(project, plaza)
            if rel not in out["views"]:
                out["views"].append(rel)

    return out


def _extract_bullet_fields(text: str, keys: tuple[str, ...]) -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for match in _SCENE_FIELD_RE.finditer(text):
        key = match.group("key").strip()
        val = match.group("val").strip()
        if key in keys and key not in found and val:
            found[key] = val
    return [(k, found[k]) for k in keys if k in found]


def _extract_section_bullets(text: str, heading_pat: str, *, limit: int = 6) -> list[str]:
    match = re.search(
        rf"(?is)(?:^|\n)###?\s*{heading_pat}\s*\n(.*?)(?:\n###?\s|\n##\s|\Z)",
        text,
    )
    if not match:
        return []
    section = match.group(1)
    bullets: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            bullets.append(stripped[2:].strip())
        if len(bullets) >= limit:
            break
    return bullets


def _extract_hard_constraint_bullets(text: str, heading_pat: str, *, limit: int = 8) -> list[str]:
    """Prefer 'Hard constraints' / Required / Avoid over optional pattern menus."""
    match = re.search(
        rf"(?is)(?:^|\n)###?\s*{heading_pat}\s*\n(.*?)(?:\n###?\s|\n##\s|\Z)",
        text,
    )
    if not match:
        return []
    section = match.group(1)
    # Prefer explicit Hard constraints block inside the section.
    hard = re.search(
        r"(?is)Hard constraints?:\s*\n((?:[-*].*\n?)+)",
        section,
    )
    source = hard.group(1) if hard else section
    bullets: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("- ") or stripped.startswith("* ")):
            continue
        item = stripped[2:].strip()
        lower = item.lower()
        # Skip the long "choose ONE pattern" menu items when Hard constraints exist.
        if hard and (
            lower.startswith("carousel")
            or lower.startswith("dialogue")
            or lower.startswith("narrative")
            or lower.startswith("interactive preview")
        ):
            continue
        bullets.append(item)
        if len(bullets) >= limit:
            break
    if hard:
        bullets.insert(
            0,
            "Pick ONE onboarding pattern from Scene Brief "
            "(carousel / dialogue / narrative / interactive preview)",
        )
    return bullets[:limit]


def extract_page_scene_brief(page_md: str, page_key: str) -> list[str]:
    """Return short natural-language constraints from a pages/*.md Scene Brief."""
    lines: list[str] = []
    keys = _SCENE_KEYS_WELCOME if page_key == "welcome" else _SCENE_KEYS_HUB
    for key, val in _extract_bullet_fields(page_md, keys):
        lines.append(f"{key}: {val}")

    if page_key == "welcome":
        for bullet in _extract_hard_constraint_bullets(
            page_md, r"Onboarding Pattern Guidance", limit=7
        ):
            lines.append(bullet)
        for bullet in _extract_section_bullets(page_md, r"Component Overrides", limit=10):
            if bullet.lower().startswith(("required:", "avoid:")):
                lines.append(bullet)
    else:
        for bullet in _extract_section_bullets(page_md, r"Hub Identity Guidance", limit=8):
            lines.append(bullet)
        for bullet in _extract_section_bullets(page_md, r"Component Overrides", limit=10):
            if bullet.lower().startswith(("required:", "avoid:")):
                lines.append(bullet)

    # De-dupe while preserving order; cap length for prompt budgets.
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        cleaned = re.sub(r"\s+", " ", line).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
        if len(out) >= 18:
            break
    return out


def format_welcome_tab1_frontload_block(workspace: Path, app_name: str) -> str:
    """Natural-language Scene Brief excerpts for Welcome + Tab1 (front-loaded)."""
    workspace = workspace.expanduser().resolve()
    ds = design_system_dir_for_app(workspace, app_name)
    pages_dir = ds / "pages"
    if not pages_dir.is_dir():
        return ""

    chunks: list[str] = [
        "## Front-loaded visual depth (Welcome + Tab1)",
        "",
        "Implement these Scene Brief constraints **before** inventing layout.",
        "Do **not** ship a compliance-only skeleton.",
        "",
    ]
    any_page = False
    for page_key in _FRONTLOAD_PAGES:
        path = pages_dir / f"{page_key}.md"
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        brief = extract_page_scene_brief(text, page_key)
        if not brief:
            continue
        any_page = True
        title = "Welcome" if page_key == "welcome" else "Tab 1 / Hub"
        chunks.append(f"### {title} — from `{_rel(workspace, path)}`")
        chunks.append("")
        for item in brief:
            chunks.append(f"- {item}")
        chunks.append("")

    if not any_page:
        return ""
    return "\n".join(chunks).rstrip() + "\n"


def format_page_implementation_prompt_block(workspace: Path, app_name: str) -> str:
    """Injected as ${PAGE_OVERRIDES_BLOCK} — front-load Scene Brief + path index."""
    workspace = workspace.expanduser().resolve()
    if not is_h5_vite_project(workspace):
        return ""

    index = collect_page_spec_file_index(workspace, app_name)
    lines = [
        "[H5 page specs — Welcome/Tab1 Scene Brief inlined below; other pages are path index]",
        "- Create full `h5/` per `docs/H5壳Vite工程规范.md` (no repo code template).",
        "- Pipeline generates kit skeleton at `skill-adapt/kit-skeleton.css`; Agent extends into `h5/src/styles/kit.css`.",
        "- All interactive elements MUST use `c-{prefix}-btn|input|checkbox|link|chip` — no bare `<button>`/`<input>`/`<a>`.",
        "",
    ]

    front = format_welcome_tab1_frontload_block(workspace, app_name)
    if front:
        # Strip markdown H2 for prompt-block embedding; keep ### subsections.
        body = front.replace("## Front-loaded visual depth (Welcome + Tab1)\n\n", "")
        lines.append("**Front-loaded visual depth (Welcome + Tab1):**")
        lines.append("")
        lines.extend(body.splitlines())
        lines.append("")

    if index["design_system_pages"]:
        lines.append("**design-system/pages/ (per-page visual + IA overrides):**")
        for path in index["design_system_pages"]:
            lines.append(f"- `{path}`")
        lines.append("")

    if index["design_system_root"]:
        lines.append("**design-system/ (stack + master):**")
        for path in index["design_system_root"]:
            lines.append(f"- `{path}`")
        lines.append("")

    if index["product_locks"]:
        lines.append("**Product + locks:**")
        for path in index["product_locks"]:
            lines.append(f"- `{path}`")
        lines.append("")

    if index["views"]:
        lines.append("**Router views (Agent implements markup + styles):**")
        for path in dict.fromkeys(index["views"]):
            lines.append(f"- `{path}`")
        lines.append("")

    if len(lines) <= 4:
        lines.append("- (no per-app page overrides yet — run skill.pages or add design-system/pages/*.md)")

    return "\n".join(lines).rstrip() + "\n"


def format_page_scaffold_prompt_block(workspace: Path, app_name: str) -> str:
    return format_page_implementation_prompt_block(workspace, app_name)
