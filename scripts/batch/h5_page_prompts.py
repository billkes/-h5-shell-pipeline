"""Per-app H5 page spec file index for Agent prompt — paths only, no inline norm prose."""

from __future__ import annotations

from pathlib import Path

from batch.h5_legal_ui import project_needs_legal_ui
from batch.h5_page_scaffold import _discover_scaffold_targets, _router_includes_route
from batch.h5_vite_gate import h5_src_dir, is_h5_vite_project
from batch.uupm_design_system import design_system_dir_for_app, master_path_for_app


def _rel(project: Path, path: Path) -> str:
    try:
        return path.relative_to(project).as_posix()
    except ValueError:
        return str(path)


def _existing(project: Path, rel: str) -> str | None:
    path = project / rel
    return _rel(project, path) if path.is_file() else None


def collect_page_spec_file_index(project: Path, app_name: str) -> dict[str, list[str]]:
    """Return grouped spec paths that exist on disk (content NOT inlined)."""
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
    stack = ds / "stack-h5-vite.md"
    if stack.is_file():
        out["design_system_root"].append(_rel(project, stack))
    ux = ds / "ux-checklist.md"
    if ux.is_file():
        out["design_system_root"].append(_rel(project, ux))
    pages_dir = ds / "pages"
    if pages_dir.is_dir():
        for path in sorted(pages_dir.glob("*.md")):
            out["design_system_pages"].append(_rel(project, path))

    for rel in (
        "功能文档.md",
        "视觉蓝图.md",
        "本包视觉锁.json",
        "skill-input/context.json",
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


def format_page_implementation_prompt_block(workspace: Path, app_name: str) -> str:
    """Injected as ${PAGE_OVERRIDES_BLOCK} — file locations only."""
    workspace = workspace.expanduser().resolve()
    if not is_h5_vite_project(workspace):
        return ""

    index = collect_page_spec_file_index(workspace, app_name)
    lines = [
        "[H5 page specs — read files below; this block is an index only]",
        "- Create full `h5/` per `docs/H5壳Vite工程规范.md` (no repo code template).",
        "- Norm prose lives in the listed paths (and in RequiredReading repo docs).",
        "- Pipeline does not generate page Vue/CSS; `dev.h5.gate` validates implementation.",
        "",
    ]

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
