"""Lightweight post-Agent gates for PM / Designer phase deliverables."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# V2 visual blueprint mandatory sections (heading substring match, case-insensitive).
VISUAL_BLUEPRINT_V2_SECTIONS: tuple[str, ...] = (
    "Ambient Canvas",
    "Overlay & Feedback",
    "Export Card Composition",
    "Confirmation Dialog Inventory",
    "List Row Anatomy",
    "Detail Page Pattern",
    "Modal Interior Spec",
    "Form & Input Canon",
    "Tag & Filter Chip Canon",
    "IAP Store Layout",
    "Welcome Gate Canon",
    "Hub Home Canon",
    "Component Selection",
    "Package Token Overrides",
)

VISUAL_LOCK_V2_KEYS: tuple[str, ...] = (
    "ambientCanvas",
    "overlayTokens",
    "exportCards",
    "listRowSpec",
    "chipSpec",
    "formFieldSpec",
    "welcomeSpec",
    "componentSelection",
    "baselineReference",
)


@dataclass
class PlanGateResult:
    """plan.gate split: hard = block pipeline; soft = warn and continue (default)."""

    hard: list[str] = field(default_factory=list)
    soft: list[str] = field(default_factory=list)

    def ok(self, *, strict: bool = False) -> bool:
        if self.hard:
            return False
        if strict and self.soft:
            return False
        return True

    def all_issues(self) -> list[str]:
        return list(self.hard) + list(self.soft)


def write_plan_gate_report(workspace: Path, result: PlanGateResult, *, strict: bool) -> Path:
    """Persist gate outcome for resume / audit."""
    from batch.interaction_topology import plan_gate_strict

    path = workspace / "plan-gate-report.json"
    repair_history: list = []
    if path.is_file():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(prev, dict) and isinstance(prev.get("repairHistory"), list):
                repair_history = prev["repairHistory"]
        except json.JSONDecodeError:
            pass

    payload = {
        "strict": strict or plan_gate_strict(),
        "passed": result.ok(strict=strict or plan_gate_strict()),
        "hard": result.hard,
        "soft": result.soft,
        "repairHistory": repair_history,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _section_present(text: str, heading_fragment: str) -> bool:
    """True when a markdown heading contains the fragment."""
    frag = heading_fragment.lower()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        if frag in stripped.lower():
            return True
    return False


def _count_export_flows_in_spec(spec_text: str) -> int:
    """Count export/save flow bullets under 功能文档 Export section (minimum 1)."""
    match = re.search(
        r"(?is)(?:^|\n)#+\s*.*export\s*/\s*save\s+flow.*?\n(.*?)(?:\n#+\s|\Z)",
        spec_text,
    )
    if not match:
        return 1
    block = match.group(1)
    numbered = re.findall(r"^\s*\d+[.)]\s+\S", block, re.M)
    if numbered:
        return len(numbered)
    bullets = re.findall(r"^\s*(?:[-*]|\d+[.)])\s+\S", block, re.M)
    filtered = [
        bullet
        for bullet in bullets
        if not re.search(
            r"export\s+record|audit\s+log|metadata|append\s+exportrecord",
            bullet,
            re.I,
        )
    ]
    return max(len(filtered), 1)


def _count_export_compositions(visual_text: str) -> int:
    """Count export composition subsections, table rows, or layer-stack blocks."""
    if not _section_present(visual_text, "Export Card Composition"):
        return 0
    section = _extract_section(visual_text, "Export Card Composition")
    headings = re.findall(r"^###+\s+\S", section, re.M)
    stacks = len(re.findall(r"layer\s+stack", section, re.I))
    table_rows = 0
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or re.match(r"^:?-+:?$", cells[0]):
            continue
        first = cells[0].lower()
        if first in ("flow", "流程", "name", "export flow"):
            continue
        table_rows += 1
    return max(len(headings), stacks, table_rows, 1 if section.strip() else 0)


def _extract_section(text: str, heading_fragment: str) -> str:
    """Return markdown body from first matching heading until next same-or-higher level heading."""
    lines = text.splitlines()
    start: int | None = None
    start_level = 0
    frag = heading_fragment.lower()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        title = stripped[level:].strip().lower()
        if frag in title:
            start = i + 1
            start_level = level
            break
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= start_level:
                break
        body.append(line)
    return "\n".join(body)


def _verify_ambient_canvas_section(
    visual_text: str,
    *,
    min_scene_rows: int = 4,
) -> list[str]:
    """Ambient Canvas Canon depth — theme background, not flat SaaS wash."""
    issues: list[str] = []
    if not _section_present(visual_text, "Ambient Canvas"):
        return issues

    section = _extract_section(visual_text, "Ambient Canvas")
    if not section.strip():
        issues.append("视觉蓝图.md Ambient Canvas 章节为空")
        return issues

    lower = section.lower()
    if "layer" not in lower and "stack" not in lower:
        issues.append("视觉蓝图.md Ambient Canvas 须声明 layer stack（base/mesh/grid/motif）")
    if "scene" not in lower and "route" not in lower:
        issues.append(
            f"视觉蓝图.md Ambient Canvas 须含 scene/route 映射表（≥{min_scene_rows} 行）"
        )
    else:
        rows = re.findall(r"^\s*\|", section, re.M)
        if len(rows) < min_scene_rows:
            issues.append(
                f"视觉蓝图.md Ambient Canvas scene 表须 ≥{min_scene_rows} 数据行"
            )
    if "ambient" not in lower and "canvas" not in lower:
        issues.append("视觉蓝图.md Ambient Canvas 须引用 ambient token（--{prefix}-ambient-*）")
    if "herovisualmotif" not in lower.replace(" ", "") and "hero visual" not in lower:
        issues.append("视觉蓝图.md Ambient Canvas 须绑定 heroVisualMotif / key_effects")

    return issues


def _verify_visual_blueprint_depth(
    visual_text: str,
    spec_text: str = "",
    *,
    pack_type: str = "",
) -> list[str]:
    """V2 depth gate for 视觉蓝图.md."""
    from batch.screen_inventory import (
        ambient_scene_min_rows,
        filter_blueprint_v2_sections,
        parse_h5_routes,
    )

    issues: list[str] = []
    if len(visual_text.strip()) < 800:
        issues.append("视觉蓝图.md 内容过短（V2 深度模板要求 ≥800 字符）")

    routes = parse_h5_routes(spec_text)
    sections = filter_blueprint_v2_sections(VISUAL_BLUEPRINT_V2_SECTIONS, routes)

    for section in sections:
        if not _section_present(visual_text, section):
            issues.append(f"视觉蓝图.md 缺少 V2 章节: {section}")

    form_section = _extract_section(visual_text, "Form & Input Canon")
    if form_section and not re.search(
        r"hintStyle.*style|style.*hintStyle|hint.*input.*same.*token|same typography token",
        form_section,
        re.I | re.S,
    ):
        issues.append(
            "视觉蓝图.md Form & Input Canon 须声明 hintStyle 与 style 使用同一 typography token"
        )

    from batch.component_kit_index import verify_component_kit_blueprint

    issues.extend(verify_component_kit_blueprint(visual_text, pack_type=pack_type))

    if spec_text:
        expected_exports = _count_export_flows_in_spec(spec_text)
        actual_exports = _count_export_compositions(visual_text)
        if actual_exports < expected_exports:
            issues.append(
                f"视觉蓝图.md Export Card Composition 条目不足"
                f"（功能文档 {expected_exports} 条 export flow，蓝图 {actual_exports} 条）"
            )

    export_section = _extract_section(visual_text, "Export Card Composition")
    if export_section and "layer stack" not in export_section.lower():
        issues.append("视觉蓝图.md Export Card Composition 须含 Layer stack（frame + dynamic fields）")

    feedback = _extract_section(visual_text, "Overlay & Feedback")
    if feedback:
        rows = re.findall(r"^\s*\|", feedback, re.M)
        if len(rows) < 3:
            issues.append("视觉蓝图.md Overlay & Feedback 须含表格（≥2 数据行）")

    from batch.welcome_canon import verify_welcome_blueprint_section
    from batch.hub_canon import verify_hub_blueprint_section

    issues.extend(verify_welcome_blueprint_section(visual_text, spec_text=spec_text))
    issues.extend(verify_hub_blueprint_section(visual_text, spec_text=spec_text))
    issues.extend(
        _verify_ambient_canvas_section(
            visual_text,
            min_scene_rows=ambient_scene_min_rows(routes),
        )
    )

    return issues


def _verify_visual_lock_depth(
    data: dict,
    *,
    h5_shell: bool = False,
    spec_text: str = "",
    pack_type: str = "",
) -> list[str]:
    """V2 depth gate for 本包视觉锁.json extended keys."""
    from batch.screen_inventory import filter_visual_lock_v2_keys, parse_h5_routes

    issues: list[str] = []
    lock_keys = filter_visual_lock_v2_keys(
        VISUAL_LOCK_V2_KEYS,
        parse_h5_routes(spec_text),
    )
    for key in lock_keys:
        if key not in data:
            issues.append(f"本包视觉锁.json 缺少 V2 字段: {key}")
            continue
        val = data[key]
        if key == "exportCards":
            if not isinstance(val, list) or len(val) < 1:
                issues.append("本包视觉锁.json exportCards 须为非空 array")
        elif key == "overlayTokens":
            if not isinstance(val, dict) or not val:
                issues.append("本包视觉锁.json overlayTokens 须为非空 object")
        elif key == "ambientCanvas":
            if not isinstance(val, dict) or not val:
                issues.append("本包视觉锁.json ambientCanvas 须为非空 object")
            elif not val.get("motifKey") or not val.get("scenes"):
                issues.append(
                    "本包视觉锁.json ambientCanvas 须含 motifKey + scenes（route→scene 映射）"
                )
        elif key == "formFieldSpec":
            if isinstance(val, dict) and not val.get("hintUsesSameToken"):
                issues.append("本包视觉锁.json formFieldSpec.hintUsesSameToken 须为 true")
        elif key == "componentSelection":
            if not isinstance(val, list) or len(val) < 1:
                issues.append("本包视觉锁.json componentSelection 须为非空 array")
            else:
                from batch.component_kit_index import (
                    parse_lock_component_entry,
                    validate_selection_ids,
                )

                kit_ids: list[str] = []
                for i, item in enumerate(val):
                    parsed = parse_lock_component_entry(item)
                    if parsed:
                        kit_ids.append(parsed)
                        continue
                    if isinstance(item, str):
                        stripped = item.strip().lower()
                        if stripped in ("baseline_h5", "baseline") or stripped.startswith(
                            "baseline_"
                        ):
                            continue
                    if isinstance(item, dict):
                        cid = str(item.get("id") or "").strip()
                        cat = str(item.get("category") or "").strip()
                        if not cid or not cat:
                            issues.append(
                                f"本包视觉锁.json componentSelection[{i}] 须为 "
                                "category/id 字符串或含 id+category 的 object"
                            )
                    elif isinstance(item, str) and item.strip():
                        issues.append(
                            f"本包视觉锁.json componentSelection[{i}] 无效 kit id: {item.strip()!r}"
                        )
                    else:
                        issues.append(
                            f"本包视觉锁.json componentSelection[{i}] 须为 "
                            "category/id 字符串或 object"
                        )
                if not kit_ids:
                    issues.append("本包视觉锁.json componentSelection 须含至少一个有效 kit id")
                issues.extend(
                    validate_selection_ids(
                        kit_ids,
                        pack_type=pack_type or ("h5_shell" if h5_shell else ""),
                    )
                )
        elif key == "baselineReference":
            from batch.component_kit_index import resolve_baseline_reference

            paths = resolve_baseline_reference(val)
            if h5_shell:
                if not paths["h5"]:
                    issues.append("本包视觉锁.json baselineReference 须含 h5 路径（h5_shell）")
            elif not paths["flutter"]:
                issues.append("本包视觉锁.json baselineReference 须含 flutter 路径")

    from batch.welcome_canon import verify_welcome_visual_lock

    issues.extend(verify_welcome_visual_lock(data, spec_text=spec_text))
    return issues


def _register_file(workspace: Path) -> Path | None:
    for name in ("本包登记信息.json", "package-register.json"):
        path = workspace / name
        if path.is_file():
            return path
    return None


_NEGATION_PREFIX = re.compile(
    r"^\s*(?:no|not|without|never|do\s+not|don't|禁止|勿|不要|无需|不得)\b",
    re.I,
)


def _line_normalized_for_negation(line: str) -> str:
    """Strip list markers / markdown bold so '- **No per-step...' reads as negation."""
    s = line.strip()
    s = re.sub(r"^[-*+]\s+", "", s)
    s = re.sub(r"^\d+\.\s+", "", s)
    s = re.sub(r"\*\*", "", s)
    return s


def _line_has_negation(line: str) -> bool:
    return _NEGATION_PREFIX.search(_line_normalized_for_negation(line)) is not None


def _line_disclaims_sdk_lock(line: str) -> bool:
    normalized = _line_normalized_for_negation(line)
    return re.search(
        r"(?:do\s+not|don't|禁止|勿|不要|无需|不得)\s*(?:re-)?pin.*flutter",
        normalized,
        re.I,
    ) is not None


def _plan_repeats_sdk_lock(text: str) -> bool:
    """True when 产包计划 affirmatively pins flutter/dart SDK (not 'do not re-pin' disclaimers)."""
    for line in text.splitlines():
        if _line_has_negation(line) or _line_disclaims_sdk_lock(line):
            continue
        if re.search(r"re-?pin\s+flutter|pin\s+flutter|flutter/dart\s+\+|锁定\s*flutter", line, re.I):
            return True
    return False


def _plan_has_per_step_checkpoints(text: str) -> bool:
    """True when 产包计划 requires per-step analyze/checkpoints (not 'no per-step' disclaimers)."""
    for line in text.splitlines():
        if _line_has_negation(line) and re.search(r"per-step|每步验收", line, re.I):
            continue
        if re.search(
            r"do\s+not\s+require\s+analyze|do\s+not\s+require\s+.*\s+between\s+§",
            line,
            re.I,
        ):
            continue
        if re.search(
            r"per-step\s+acceptance|每步验收|step\s+\d+:\s*analyze|between\s+steps.*analyze",
            line,
            re.I,
        ):
            return True
    return False


def verify_phase1_pm_outputs(
    workspace: Path,
    *,
    tool_flutter: bool,
    videostream: bool,
    h5_shell: bool = False,
    csv_full_name: str = "",
) -> tuple[bool, list[str]]:
    """Return (ok, issues) after Phase 1 Agent."""
    issues: list[str] = []
    spec = workspace / "功能文档.md"
    if not spec.is_file() or spec.stat().st_size < 200:
        issues.append("缺少 功能文档.md 或内容过短")

    reg = _register_file(workspace)
    if reg is None:
        issues.append("缺少 本包登记信息.json（或 package-register.json）")
    else:
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                issues.append("本包登记信息.json 不是 JSON object")
            elif tool_flutter:
                for key in (
                    "themeAngle",
                    "mainFeature",
                    "tab1Name",
                    "tab2Name",
                    "tab3Name",
                    "codeAntiCorrelation",
                ):
                    if not data.get(key):
                        issues.append(f"本包登记信息.json 缺少字段: {key}")
            elif h5_shell:
                for key in (
                    "themeAngle",
                    "shellRuntime",
                    "appSlug",
                    "h5EntryUrl",
                    "h5EntryUrlDev",
                    "h5EntryUrlProd",
                    "h5SourceRoot",
                    "h5BuildCommand",
                    "h5SiteRoot",
                    "h5SiteEntry",
                    "h5VaultPattern",
                    "h5VaultLayout",
                    "bridgeDeckSelections",
                    "bridgeCapabilities",
                    "kitDeckSelections",
                    "codeAntiCorrelation",
                ):
                    if not data.get(key):
                        issues.append(f"本包登记信息.json 缺少字段: {key}")
            else:
                for key in (
                    "themeAngle",
                    "innovationTabName",
                    "feedInnovation",
                    "detailInnovation",
                ):
                    if not data.get(key):
                        issues.append(f"本包登记信息.json 缺少字段: {key}")
        except json.JSONDecodeError:
            issues.append("本包登记信息.json JSON 不合法")

    content = workspace / "默认内容列表.json"
    if h5_shell:
        pass
    elif tool_flutter:
        if content.is_file():
            try:
                arr = json.loads(content.read_text(encoding="utf-8"))
                if not isinstance(arr, list):
                    issues.append("默认内容列表.json 必须是 JSON array（工具包可为 []）")
            except json.JSONDecodeError:
                issues.append("默认内容列表.json JSON 不合法")
    else:
        if not content.is_file():
            issues.append("缺少 默认内容列表.json")
        else:
            try:
                arr = json.loads(content.read_text(encoding="utf-8"))
                if not isinstance(arr, list) or len(arr) < 2:
                    issues.append("默认内容列表.json 须为至少 2 项的 array")
            except json.JSONDecodeError:
                issues.append("默认内容列表.json JSON 不合法")

    if csv_full_name:
        if h5_shell:
            if spec.is_file():
                spec_text = spec.read_text(encoding="utf-8", errors="replace")
                if "产品概述" not in spec_text and "Product Overview" not in spec_text:
                    issues.append("功能文档.md 缺少 #### 产品概述 (Product Overview) 章节")
            legacy_product = workspace / f"{csv_full_name}.md"
            if legacy_product.is_file() and not spec.is_file():
                pass  # legacy workspace — gate still accepts standalone file until spec exists
        else:
            product_doc = workspace / f"{csv_full_name}.md"
            if not product_doc.is_file():
                issues.append(f"缺少产品文档: {csv_full_name}.md")

    if videostream and spec.is_file():
        text = spec.read_text(encoding="utf-8", errors="replace")
        if "Feed Innovation" not in text and "feed" not in text.lower():
            issues.append("视频流包 功能文档.md 应包含 Feed 相关创新描述")

    return (len(issues) == 0, issues)


def verify_phase2_designer_outputs(workspace: Path) -> tuple[bool, list[str]]:
    """Return (ok, issues) after Phase 2 Agent."""
    issues: list[str] = []
    visual = workspace / "视觉蓝图.md"
    lock = workspace / "本包视觉锁.json"
    spec = workspace / "功能文档.md"
    spec_text = ""
    if spec.is_file():
        spec_text = spec.read_text(encoding="utf-8", errors="replace")

    register: dict = {}
    reg_path = workspace / "本包登记信息.json"
    if reg_path.is_file():
        try:
            parsed = json.loads(reg_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                register = parsed
        except json.JSONDecodeError:
            pass
    pack_type = str(register.get("packType") or "").strip()
    if not pack_type and (
        register.get("h5EntryUrl")
        or register.get("h5SiteRoot")
        or register.get("bundleEntryPath")
        or register.get("h5VaultPattern")
    ):
        pack_type = "h5_shell"
    from batch.pack_type import is_h5_shell

    h5 = is_h5_shell(pack_type)

    if not h5:
        if not visual.is_file() or visual.stat().st_size < 200:
            issues.append("缺少 视觉蓝图.md 或内容过短")
        elif visual.is_file():
            visual_text = visual.read_text(encoding="utf-8", errors="replace")
            issues.extend(
                _verify_visual_blueprint_depth(visual_text, spec_text, pack_type=pack_type)
            )
    # h5_shell: 视觉蓝图.md 已退役；UI 规范以 design-system + skill-adapt + 本包视觉锁 为准

    if not lock.is_file():
        issues.append("缺少 本包视觉锁.json")
    else:
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                issues.append("本包视觉锁.json 不是 JSON object")
            else:
                if not data.get("designerDeckSelections"):
                    issues.append("本包视觉锁.json 缺少 designerDeckSelections")
                if not data.get("colorTokens"):
                    issues.append("本包视觉锁.json 缺少 colorTokens")
                issues.extend(
                    _verify_visual_lock_depth(
                        data,
                        h5_shell=h5,
                        spec_text=spec_text,
                        pack_type=pack_type,
                    )
                )
        except json.JSONDecodeError:
            issues.append("本包视觉锁.json JSON 不合法")
    return (len(issues) == 0, issues)


def verify_pm_ui_plan_outputs(
    workspace: Path,
    *,
    tool_flutter: bool,
    videostream: bool,
    h5_shell: bool = False,
    csv_full_name: str = "",
    app_name: str = "",
    project_dir: Path | None = None,
    sibling_workspaces: list[Path] | None = None,
) -> PlanGateResult:
    """V3 Phase 1 gate: PM+UI+Plan — hard vs soft split (default: soft warns, no断线)."""
    hard: list[str] = []
    soft: list[str] = []

    def _hard(msg: str) -> None:
        hard.append(msg)

    def _soft(msg: str) -> None:
        soft.append(msg)

    ok_pm, issues_pm = verify_phase1_pm_outputs(
        workspace,
        tool_flutter=tool_flutter,
        videostream=videostream,
        h5_shell=h5_shell,
        csv_full_name=csv_full_name,
    )
    for issue in issues_pm:
        if issue.startswith("缺少 功能文档") or issue.startswith("缺少 本包登记"):
            _hard(issue)
        elif "JSON 不合法" in issue or "不是 JSON object" in issue:
            _hard(issue)
        elif issue.startswith("缺少字段"):
            _hard(issue)
        elif issue.startswith("缺少产品文档"):
            _soft(issue)
        elif "产品概述" in issue:
            _soft(issue)
        elif not ok_pm:
            _hard(issue)
        else:
            _soft(issue)

    ok_ui, issues_ui = verify_phase2_designer_outputs(workspace)
    for issue in issues_ui:
        if issue.startswith("缺少 本包视觉锁"):
            _hard(issue)
        elif issue.startswith("缺少 视觉蓝图"):
            if h5_shell:
                _soft(issue)  # legacy file; skill chain replaces blueprint
            else:
                _hard(issue)
        elif "JSON 不合法" in issue or "不是 JSON object" in issue:
            _hard(issue)
        elif not ok_ui:
            _soft(issue)
        else:
            _soft(issue)

    from batch.uupm_design_system import find_design_system_master

    master = find_design_system_master(workspace, app_name)
    if master is None or master.stat().st_size < 200:
        _hard("缺少 design-system MASTER.md（agent.design 产物）")
    design_audit = workspace / "skill-adapt" / "design-audit.md"
    if not design_audit.is_file() or design_audit.stat().st_size < 40:
        _hard("缺少 skill-adapt/design-audit.md（agent.design 必交）")
    pointer = workspace / "设计系统建议.md"
    if not pointer.is_file():
        _soft("缺少 设计系统建议.md（可选指针）")
    adapt_brief = workspace / "skill-adapt" / "design-brief.md"
    if not adapt_brief.is_file():
        _soft("缺少 skill-adapt/design-brief.md（agent.design 产物）")

    ux_checklist = None
    for path in workspace.glob("design-system/*/ux-checklist.md"):
        ux_checklist = path
        break
    if ux_checklist is None or ux_checklist.stat().st_size < 80:
        _soft("缺少 design-system/*/ux-checklist.md（agent.design 域检索产物）")

    if h5_shell:
        from batch.screen_inventory import page_slugs_from_spec

        spec_path = workspace / "功能文档.md"
        spec_for_pages = (
            spec_path.read_text(encoding="utf-8", errors="replace")
            if spec_path.is_file()
            else ""
        )
        expected_slugs = page_slugs_from_spec(spec_for_pages)
        pages_dir = None
        for path in workspace.glob("design-system/*/pages"):
            if path.is_dir():
                pages_dir = path
                break
        page_files = list(pages_dir.glob("*.md")) if pages_dir else []
        page_count = len(page_files)
        if expected_slugs:
            if page_count < len(expected_slugs):
                _soft(
                    f"design-system pages 不足（当前 {page_count}，"
                    f"Screen Inventory 需要 {len(expected_slugs)}）"
                )
            present = {p.stem for p in page_files}
            orphans = sorted(present - set(expected_slugs))
            if orphans:
                _soft(
                    f"design-system pages 含 Inventory 未声明项: "
                    f"{orphans[:8]}{'…' if len(orphans) > 8 else ''}"
                )
        elif page_count > 0:
            _soft(
                f"design-system pages 存在 {page_count} 个文件，"
                "但 Screen Inventory 未解析到 H5 路由"
            )

        tokens_css = workspace / "skill-adapt" / "design-tokens.css"
        if not tokens_css.is_file():
            _soft("缺少 skill-adapt/design-tokens.css（skill.tokens 产物）")

        from batch.h5_legal_md_gate import verify_h5_legal_md

        for issue in verify_h5_legal_md(workspace, project_dir=project_dir):
            _hard(issue)

    visual = workspace / "视觉蓝图.md"
    if visual.is_file() and h5_shell:
        vtext = visual.read_text(encoding="utf-8", errors="replace")
        if "ux-checklist" not in vtext.lower() and "ambient canvas" not in vtext.lower():
            _soft("视觉蓝图.md 应引用 ux-checklist 或 Ambient Canvas enrich 产物（legacy；新包可不产此文件）")



    spec = workspace / "功能文档.md"
    if spec.is_file():
        spec_text = spec.read_text(encoding="utf-8", errors="replace")
        if "Data Contract" not in spec_text and "数据契约" not in spec_text:
            _soft("功能文档.md 缺少 Data Contract / 数据契约 章节")
        if h5_shell:
            from batch.spec_business_depth import (
                resolve_tier_from_workspace,
                spec_depth_gate_enabled,
                verify_spec_business_depth,
            )

            if spec_depth_gate_enabled():
                tier_id = resolve_tier_from_workspace(workspace)
                for issue in verify_spec_business_depth(spec_text, tier_id=tier_id):
                    _soft(issue)

            if project_dir is not None:
                import os
                from batch.interaction_topology import (
                    verify_flow_topology_soft_for_workspace,
                )

                if os.environ.get("ENABLE_FLOW_TOPOLOGY_GATE", "1").strip().lower() not in (
                    "0",
                    "false",
                    "no",
                ):
                    for issue in verify_flow_topology_soft_for_workspace(
                        workspace,
                        project_dir=project_dir,
                        sibling_workspaces=sibling_workspaces,
                    ):
                        _soft(issue)

    from batch.selection_gate import verify_selection_plan

    for issue in verify_selection_plan(
        workspace,
        pack_type="h5_shell" if h5_shell else (
            "tool_flutter" if tool_flutter else (
                "videostream" if videostream else "contentpack"
            )
        ),
        h5_shell=h5_shell,
    ):
        _soft(issue)

    seen: set[str] = set()
    deduped_soft: list[str] = []
    for msg in soft:
        if msg not in seen:
            seen.add(msg)
            deduped_soft.append(msg)

    return PlanGateResult(hard=hard, soft=deduped_soft)
