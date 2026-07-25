"""Write path-only Agent indexes under skill-input/ — no norm prose in prompts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

AgentPhase = Literal[
    "plan",
    "plan_spec",
    "plan_docs",
    "plan_pack",
    "shell",
    "h5",
    "preview",
    "repair",
    "h5_build_repair",
]

SPEC_INDEX_REL = "skill-input/agent-spec-index.md"
# Role reading list inside the package workspace (not an external brain).
WORKSPACE_FOCUS_REL = "skill-input/agent-workspace-focus.md"
# Legacy filename kept as a one-line pointer for older prompts / resumes.
BRAIN_FOCUS_REL = "skill-input/agent-brain-focus.md"
REPAIR_BRIEF_REL = "skill-input/plan-gate-repair-brief.md"
H5_BUILD_REPAIR_BRIEF_REL = "skill-input/h5-build-repair-brief.md"

WORKSPACE_SCOPE_LINE = (
    "Required reading and tools may only use paths under this workspace root. "
    "Paths outside the app root are out of scope."
)

_PLAN_NORM_DOCS: tuple[str, ...] = (
    "H5壳Plan交付规范.md",
    "H5壳Pack约束.md",
    "H5壳功能文档深度标准.md",
    "H5壳交互拓扑与PlanGate策略.md",
    "H5壳产品文档格式.md",
    "H5壳Micro-UI Kit约束.md",
    "法律协议规范.md",
    "data/static/component_kit/README.md",
    "data/static/component_kit/baseline.md",
    "data/static/component_kit/tokens.md",
)

_SHELL_NORM_DOCS: tuple[str, ...] = (
    "H5壳Pack约束.md",
    "H5-Bridge协议.md",
    "H5壳业务流程文字版.md",
    "H5壳启动闪屏规范.md",
    "H5壳Swift实现规范.md",
    "H5壳OC实现规范.md",
    "H5壳WKWebView性能与层叠规范.md",
    "架构模式矩阵.md",
    "状态管理矩阵.md",
    "编程人设风格.md",
    "命名混淆规则.md",
)

_H5_NORM_DOCS: tuple[str, ...] = (
    "H5壳H5实现检查清单.md",
    "H5壳Vite工程规范.md",
    "H5壳Legal弹层规范.md",
    "H5壳广场页规范.md",
    "H5壳Overlay路由规范.md",
    "H5去风味规范.md",
    "H5壳Pack约束.md",
    "H5壳Micro-UI Kit约束.md",
    "H5-Bridge协议.md",
    "H5壳Vault合规维护规范.md",
    "data/static/h5_snippets/bridge/README.md",
    "data/static/h5_snippets/bridge/browserMock.ts",
    "data/static/h5_snippets/legal/README.md",
    "data/static/h5_snippets/legal/legalLinks.ts",
)

_PREVIEW_NORM_DOCS: tuple[str, ...] = (
    "H5壳Pack约束.md",
    "_preview/preview-canonical.md",
)


def _rel(workspace: Path, path: Path) -> str:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError:
        return str(path)


def _existing(workspace: Path, rel: str) -> str | None:
    path = workspace / rel
    return rel if path.is_file() or path.is_dir() else None


def _dedupe_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _section(title: str, paths: list[str]) -> list[str]:
    paths = _dedupe_paths([p for p in paths if p])
    if not paths:
        return []
    lines = [f"## {title}", ""]
    for p in paths:
        lines.append(f"- `{p}`")
    lines.append("")
    return lines


def _collect_skill_adapt_paths(workspace: Path) -> list[str]:
    out: list[str] = []
    for rel in (
        "skill-adapt/design-brief.md",
        "skill-adapt/ambient-canvas-brief.md",
        "skill-adapt/selected-designer.json",
        "skill-adapt/selected-candidate.json",
        "skill-adapt/design-tokens.css",
        "skill-adapt/css-motion-brief.md",
        "skill-adapt/icon-manifest.json",
        "skill-adapt/icon-sprite-manifest.json",
        "skill-adapt/token-impl-block.md",
        "skill-adapt/impl-ui-input.md",
        "skill-adapt/preview-approved-colors.json",
    ):
        hit = _existing(workspace, rel)
        if hit:
            out.append(hit)
    return out


def _collect_design_system_paths(workspace: Path, app_name: str) -> list[str]:
    out: list[str] = []
    try:
        from batch.uupm_design_system import design_system_dir_for_app, master_path_for_app

        master = master_path_for_app(workspace, app_name)
        if master.is_file():
            out.append(_rel(workspace, master))
        ds = design_system_dir_for_app(workspace, app_name)
        for rel in (
            "stack-vue.md",
            "stack-html-tailwind.md",
            "h5-runtime.md",
            "ux-checklist.md",
            "h5-interface-brief.md",
            "icon-brief.md",
            "typography-brief.md",
        ):
            path = ds / rel
            if path.is_file():
                out.append(_rel(workspace, path))
        pages = ds / "pages"
        if pages.is_dir():
            for path in sorted(pages.glob("*.md")):
                out.append(_rel(workspace, path))
    except Exception:
        pass
    return out


def _collect_enrich_paths(workspace: Path, app_name: str) -> list[str]:
    try:
        from batch.skill_enrich import enrich_file_paths

        return [
            _rel(workspace, p)
            for p in enrich_file_paths(workspace, app_name).values()
            if p.is_file()
        ]
    except Exception:
        return []


def _collect_page_paths(workspace: Path, app_name: str) -> list[str]:
    try:
        from batch.h5_page_prompts import collect_page_spec_file_index

        index = collect_page_spec_file_index(workspace, app_name)
        paths: list[str] = []
        for key in (
            "design_system_root",
            "design_system_pages",
            "product_locks",
            "views",
        ):
            paths.extend(index.get(key, []))
        return paths
    except Exception:
        return []


def _collect_pack_json_paths(workspace: Path) -> list[str]:
    out: list[str] = []
    for rel in (
        "本包代码组合.json",
        "本包登记信息.json",
        "本包视觉锁.json",
        "skill-input/context.json",
        "iap-catalog.generated.md",
        "功能文档.md",
        "视觉蓝图.md",
        "产包计划.md",
    ):
        hit = _existing(workspace, rel)
        if hit:
            out.append(hit)
    return out


def _collect_required_kit_ids(workspace: Path, pack_type: str) -> list[str]:
    try:
        from batch.component_kit_index import (
            extract_selection_ids_from_visual_lock,
            normalize_component_id,
        )
        from batch.selection_requirements import collect_required_selection_ids

        lock_path = workspace / "本包视觉锁.json"
        lock_ids: set[str] = set()
        if lock_path.is_file():
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                lock_ids = {
                    normalize_component_id(i)
                    for i in extract_selection_ids_from_visual_lock(data)
                }
        return sorted(
            collect_required_selection_ids(
                workspace, pack_type=pack_type, existing=lock_ids
            )
        )
    except Exception:
        return []


def _collect_preview_paths(workspace: Path, app_name: str) -> list[str]:
    out: list[str] = []
    try:
        from batch.preview_tabs import preview_canonical_path, preview_html_path

        html = preview_html_path(workspace, app_name)
        canonical = preview_canonical_path(workspace)
        if html.is_file():
            out.append(_rel(workspace, html))
        if canonical.is_file():
            out.append(_rel(workspace, canonical))
    except Exception:
        pass
    return out


def _norm_docs_for_phase(phase: AgentPhase) -> list[str]:
    mapping = {
        "plan": _PLAN_NORM_DOCS,
        "plan_spec": (
            *_PLAN_NORM_DOCS,
            "H5壳Flutter产品要求.md",
        ),
        "plan_docs": (
            "H5壳产品文档格式.md",
            "法律协议规范.md",
        ),
        "plan_pack": _PLAN_NORM_DOCS,
        "shell": _SHELL_NORM_DOCS,
        "h5": _H5_NORM_DOCS,
        "preview": _PREVIEW_NORM_DOCS,
        "repair": _PLAN_NORM_DOCS,
        "h5_build_repair": _H5_NORM_DOCS,
    }
    return list(mapping.get(phase, ()))


def write_agent_workspace_focus(
    workspace: Path,
    *,
    role_slug: str,
    role_focus: str,
) -> Path:
    """Write in-workspace role reading list (no external brain / recall roots)."""
    from batch.agent_distilled import distilled_focus_file_lines

    workspace = workspace.expanduser().resolve()
    out_path = workspace / WORKSPACE_FOCUS_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prefer = role_focus.strip()
    projected = distilled_focus_file_lines(workspace, role_slug=role_slug)
    if projected:
        prefer = prefer + "\n" + "\n".join(projected)
    body = "\n".join(
        [
            "# Workspace reading scope",
            "",
            f"Role: `{role_slug}`",
            "",
            WORKSPACE_SCOPE_LINE,
            "",
            "Prefer these workspace docs for this role:",
            prefer,
            "",
            "Also available: package `.cursor/rules/*.mdc` (written into this workspace).",
            "",
        ]
    )
    out_path.write_text(body, encoding="utf-8")
    # Legacy pointer so old Required Reading lines still resolve.
    legacy = workspace / BRAIN_FOCUS_REL
    legacy.write_text(
        "# Moved\n\n"
        "See `skill-input/agent-workspace-focus.md`.\n",
        encoding="utf-8",
    )
    return out_path


def write_agent_brain_focus(
    workspace: Path,
    *,
    role_slug: str,
    role_focus: str,
) -> Path:
    """Backward-compatible alias for :func:`write_agent_workspace_focus`."""
    return write_agent_workspace_focus(
        workspace,
        role_slug=role_slug,
        role_focus=role_focus,
    )


def prepare_agent_prompt_files(
    workspace: Path,
    *,
    phase: AgentPhase,
    app_name: str,
    pack_type: str,
    role_slug: str,
    role_focus: str,
) -> tuple[Path, Path]:
    """Write spec index + workspace focus to workspace before Agent run."""
    index = write_agent_spec_index(
        workspace,
        phase=phase,
        app_name=app_name,
        pack_type=pack_type,
    )
    brain = write_agent_workspace_focus(
        workspace,
        role_slug=role_slug,
        role_focus=role_focus,
    )
    return index, brain


def write_agent_spec_index(
    workspace: Path,
    *,
    phase: AgentPhase,
    app_name: str = "",
    pack_type: str = "h5_shell",
) -> Path:
    workspace = workspace.expanduser().resolve()
    out_path = workspace / SPEC_INDEX_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)

    norm_hits = [
        p for doc in _norm_docs_for_phase(phase) if (p := _existing(workspace, doc))
    ]

    lines = [
        "# Agent spec index",
        "",
        f"Phase: **{phase}**",
        "",
    ]

    # Welcome + Tab1 Scene Brief first (h5 phases) — Agent reads this before path lists.
    if phase in ("h5", "h5_build_repair", "preview"):
        try:
            from batch.h5_page_prompts import format_welcome_tab1_frontload_block

            front = format_welcome_tab1_frontload_block(workspace, app_name)
            if front:
                lines.append(front.rstrip())
                lines.append("")
        except Exception:
            pass

    lines.extend(
        [
            "Other norm prose lives in the paths below — open them after Welcome/Tab1 rules above.",
            "",
        ]
    )
    lines.extend(_section("Norm docs", norm_hits))
    lines.extend(_section("Pack locks (JSON / generated)", _collect_pack_json_paths(workspace)))

    if phase in ("plan", "plan_spec", "plan_docs", "plan_pack", "preview", "repair"):
        lines.extend(_section("skill.adapt", _collect_skill_adapt_paths(workspace)))
        lines.extend(
            _section("design-system", _collect_design_system_paths(workspace, app_name))
        )
        lines.extend(_section("skill.enrich", _collect_enrich_paths(workspace, app_name)))
        lines.extend(
            _section(
                "skill.pages / per-route specs",
                _collect_page_paths(workspace, app_name),
            )
        )
        kit_ids = _collect_required_kit_ids(workspace, pack_type)
        if kit_ids:
            lines.extend(["## Required component kit ids", ""])
            for cid in kit_ids:
                lines.append(f"- `{cid}`")
            lines.append("")

    if phase in ("plan", "plan_spec", "plan_pack", "h5", "preview"):
        lines.extend(
            _section("Tab preview (when present)", _collect_preview_paths(workspace, app_name))
        )

    if phase in ("h5", "h5_build_repair"):
        lines.extend(_section("skill.adapt (H5)", _collect_skill_adapt_paths(workspace)))
        lines.extend(_section("Per-route specs", _collect_page_paths(workspace, app_name)))
        h5_dir = workspace / "h5"
        if h5_dir.is_dir():
            lines.extend(
                _section(
                    "H5 source (repair scope)",
                    [
                        p
                        for rel in ("h5/package.json", "h5/vite.config.ts", "h5/src")
                        if (p := _existing(workspace, rel))
                    ],
                )
            )

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path


def write_plan_gate_repair_brief(
    workspace: Path,
    *,
    issue: str,
    focus: str,
    target_files: tuple[str, ...],
    constraints: str = "",
) -> Path:
    workspace = workspace.expanduser().resolve()
    out_path = workspace / REPAIR_BRIEF_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# plan.gate repair brief",
        "",
        f"**Issue:** {issue}",
        f"**Focus:** {focus}",
        "",
    ]
    if constraints.strip():
        lines.extend([f"**Constraints:** {constraints}", ""])
    lines.extend(["## Files to read and patch", ""])
    for rel in target_files:
        lines.append(f"- `{rel}`")
    lines.extend(
        [
            "",
            "## Norm docs",
            "",
            "- `skill-input/agent-spec-index.md`",
            "- `H5壳Plan交付规范.md`",
            "- `H5壳功能文档深度标准.md`",
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def write_h5_build_repair_brief(
    workspace: Path,
    *,
    issues: list[str],
    focus: str,
    round_no: int,
    max_rounds: int,
) -> Path:
    workspace = workspace.expanduser().resolve()
    out_path = workspace / H5_BUILD_REPAIR_BRIEF_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# h5.build repair brief",
        "",
        f"**Round:** {round_no}/{max_rounds}",
        f"**Focus:** {focus}",
        "",
        "## Build errors",
        "",
    ]
    for issue in issues:
        lines.append(f"```")
        lines.append(issue)
        lines.append("```")
        lines.append("")
    lines.extend(
        [
            "## Allowed paths",
            "",
            "- `h5/**` (Vue/TS/Vite only)",
            "",
            "## Forbidden",
            "",
            "- `h5_site/` (pipeline deploy output)",
            "- Plan docs (`功能文档.md`, `视觉蓝图.md`, …)",
            "- Native shell (`ios/`, `android/`, …)",
            "",
            "## Norm docs",
            "",
            "- `skill-input/agent-spec-index.md`",
            "- `H5壳Vite工程规范.md`",
            "- `H5壳H5实现检查清单.md`",
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
