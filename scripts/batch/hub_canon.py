"""Hub Home Canon — Tab 1 product-bound plan gate + H5 implementer audits."""

from __future__ import annotations

import json
import re
from pathlib import Path

from batch.h5_vite_gate import h5_src_dir, is_h5_vite_project
from batch.page_scene_spec import hub_pattern_for_topology
from batch.pack_type import is_h5_shell


def _read_register(project: Path) -> dict:
    for name in ("本包登记信息.json", "package-register.json"):
        path = project / name
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
    return {}


def _load_product_context(project: Path) -> dict:
    ctx_path = project / "skill-input" / "context.json"
    if not ctx_path.is_file():
        return {}
    try:
        data = json.loads(ctx_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _project_has_tab_roots(project: Path, spec_text: str = "") -> bool:
    from batch.screen_inventory import parse_h5_routes, parse_tab1_route, read_spec_text

    text = spec_text or read_spec_text(project)
    if parse_tab1_route(text):
        return True
    routes = parse_h5_routes(text) if text else frozenset()
    return bool(routes.intersection({"/hub", "/home", "/prepare", "/today"}))


def _spec_has_tab_roots(spec_text: str) -> bool:
    from batch.screen_inventory import parse_h5_routes, parse_tab1_route

    if parse_tab1_route(spec_text):
        return True
    return bool(
        parse_h5_routes(spec_text).intersection(
            {"/hub", "/home", "/prepare", "/today"}
        )
    )


def verify_hub_blueprint_section(
    visual_text: str,
    *,
    spec_text: str = "",
) -> list[str]:
    """Plan gate: 视觉蓝图 Hub Home Canon (Tab 1 identity)."""
    if spec_text and not _spec_has_tab_roots(spec_text):
        return []

    issues: list[str] = []
    if not re.search(r"hub\s+home\s+canon", visual_text, re.I):
        issues.append("视觉蓝图.md 缺少 V2 章节: Hub Home Canon")
        return issues

    section_match = re.search(
        r"(?is)(?:^|\n)#+\s*.*hub\s+home\s+canon.*?\n(.*?)(?:\n#+\s|\Z)",
        visual_text,
    )
    section = section_match.group(1) if section_match else ""
    if not section.strip():
        issues.append("视觉蓝图.md Hub Home Canon 章节为空")
        return issues

    rows = [
        line
        for line in section.splitlines()
        if line.strip().startswith("|") and not re.match(r"^\s*\|[-:\s|]+\|\s*$", line)
    ]
    if len(rows) < 3:
        issues.append(
            "视觉蓝图.md Hub Home Canon 须含槽位表"
            "（≥3 行：primary zone / feed / empty-state 等）"
        )

    if not re.search(
        r"primary\s*zone|主交互|signature|topology|交互拓扑",
        section,
        re.I,
    ):
        issues.append(
            "视觉蓝图.md Hub Home Canon 须声明 topology 绑定的 primary zone"
            "（禁止仅写 generic chips + KPI）"
        )

    if not re.search(
        r"audience|core\s*scene|product\s*flow|使用|人群|场景|时机|"
        r"usage\s*moment|primary\s*zone|tab\s*1|identity|"
        r"habit|streak|workspace|canvas|month|review",
        section,
        re.I,
    ):
        issues.append(
            "视觉蓝图.md Hub Home Canon 须引用 audience / coreScene / productFlow"
            "（或等价的场景/人群/时机描述）"
        )

    if not re.search(r"empty|空态", section, re.I):
        issues.append("视觉蓝图.md Hub Home Canon 须声明 empty state")

    return issues


def find_hub_view_text(project: Path) -> str:
    """Locate Tab1 / hub view source for audits."""
    src = h5_src_dir(project)
    if not src.is_dir():
        return ""

    from batch.screen_inventory import parse_tab1_route, read_spec_text

    tab1 = parse_tab1_route(read_spec_text(project))
    preferred: list[str] = []
    if tab1:
        seg = tab1.strip("/").split("/")[-1]
        if seg:
            preferred.append(f"{seg.title()}View.vue")
            preferred.append(f"{seg.capitalize()}View.vue")

    preferred.extend(
        [
            "HubView.vue",
            "HomeView.vue",
            "TodayView.vue",
            "PrepareView.vue",
            "CircleView.vue",
            "WorkspaceView.vue",
        ]
    )

    views = src / "views"
    if not views.is_dir():
        return ""

    for name in preferred:
        path = views / name
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                return ""

    # Fallback: any *View.vue whose name matches tab1 segment
    if tab1:
        seg = tab1.strip("/").split("/")[-1].lower()
        for path in sorted(views.glob("*View.vue")):
            if seg and seg in path.name.lower():
                try:
                    return path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
    return ""


def _verify_h5_hub_vite(project: Path) -> list[str]:
    issues: list[str] = []
    hub = find_hub_view_text(project)
    if not hub:
        # Soft skip when no identifiable Tab1 view yet (early scaffold).
        return issues

    if len(hub.strip()) < 80:
        issues.append("Hub/Tab1 view looks empty — implement product-bound primary zone")

    ctx = _load_product_context(project)
    constraints = ctx.get("constraints") if isinstance(ctx.get("constraints"), dict) else {}
    product = ctx.get("product") if isinstance(ctx.get("product"), dict) else {}
    topo_id = str(
        constraints.get("interactionTopology") or constraints.get("n") or ""
    ).strip()
    core_scene = str(product.get("coreScene") or "").strip()

    # Generic chip+KPI-only landing is the anti-pattern we are killing.
    has_chip_kpi_only = bool(
        re.search(r"chip", hub, re.I)
        and re.search(r"kpi|stat.?strip", hub, re.I)
        and not re.search(
            r"orbit|ring|timeline|canvas|workspace|stamp|wizard|checklist|compare|capture",
            hub,
            re.I,
        )
    )
    if has_chip_kpi_only and topo_id and topo_id not in ("T1_dashboard",):
        issues.append(
            f"Hub/Tab1: topology={topo_id} 禁止仅用 generic chip+KPI 首页"
            " — 须实现 Scene Brief 中的 primary zone"
        )

    if topo_id:
        pattern = hub_pattern_for_topology(topo_id)
        markers = pattern.get("markers") or ""
        marker_re = markers.replace(".", r"[\s_-]*")
        if marker_re and not re.search(marker_re, hub, re.I):
            issues.append(
                f"Hub/Tab1: topology={topo_id} 主交互区缺少语义线索"
                f"（期望匹配: {markers}）"
            )

    if core_scene:
        # Empty-state / CTA presence
        if not re.search(r"empty|cta|add\s+first|no\s+\w+", hub, re.I):
            issues.append("Hub/Tab1: 须含 empty state 或 Primary Workflow CTA")

    return issues


def verify_h5_hub_canon(project: Path) -> list[str]:
    """H5 implementer audit for Tab 1 product identity."""
    project = project.expanduser().resolve()
    if not is_h5_shell(str(_read_register(project).get("packType") or "")):
        return []
    if not _project_has_tab_roots(project):
        return []
    if is_h5_vite_project(project):
        return _verify_h5_hub_vite(project)
    return []
