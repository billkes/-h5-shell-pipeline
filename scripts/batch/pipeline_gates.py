"""Lightweight post-Agent gates for PM / Designer phase deliverables."""

from __future__ import annotations

import json
import re
from pathlib import Path

# V2 visual blueprint mandatory sections (heading substring match, case-insensitive).
VISUAL_BLUEPRINT_V2_SECTIONS: tuple[str, ...] = (
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
    "Component Selection",
    "Package Token Overrides",
)

VISUAL_LOCK_V2_KEYS: tuple[str, ...] = (
    "overlayTokens",
    "exportCards",
    "listRowSpec",
    "chipSpec",
    "formFieldSpec",
    "welcomeSpec",
    "componentSelection",
    "baselineReference",
)


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
    bullets = re.findall(r"^\s*(?:[-*]|\d+[.)])\s+\S", block, re.M)
    return max(len(bullets), 1)


def _count_export_compositions(visual_text: str) -> int:
    """Count export composition subsections or layer-stack blocks."""
    if not _section_present(visual_text, "Export Card Composition"):
        return 0
    section = _extract_section(visual_text, "Export Card Composition")
    headings = re.findall(r"^###+\s+\S", section, re.M)
    stacks = len(re.findall(r"layer\s+stack", section, re.I))
    return max(len(headings), stacks, 1 if section.strip() else 0)


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


def _verify_visual_blueprint_depth(
    visual_text: str,
    spec_text: str = "",
) -> list[str]:
    """V2 depth gate for 视觉蓝图.md."""
    issues: list[str] = []
    if len(visual_text.strip()) < 800:
        issues.append("视觉蓝图.md 内容过短（V2 深度模板要求 ≥800 字符）")

    for section in VISUAL_BLUEPRINT_V2_SECTIONS:
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

    issues.extend(verify_component_kit_blueprint(visual_text))

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

    issues.extend(verify_welcome_blueprint_section(visual_text))

    return issues


def _verify_visual_lock_depth(data: dict, *, h5_shell: bool = False) -> list[str]:
    """V2 depth gate for 本包视觉锁.json extended keys."""
    issues: list[str] = []
    for key in VISUAL_LOCK_V2_KEYS:
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
                issues.extend(validate_selection_ids(kit_ids))
        elif key == "baselineReference":
            from batch.component_kit_index import resolve_baseline_reference

            paths = resolve_baseline_reference(val)
            if h5_shell:
                if not paths["h5"]:
                    issues.append("本包视觉锁.json baselineReference 须含 h5 路径（h5_shell）")
            elif not paths["flutter"]:
                issues.append("本包视觉锁.json baselineReference 须含 flutter 路径")

    from batch.welcome_canon import verify_welcome_visual_lock

    issues.extend(verify_welcome_visual_lock(data))
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

    if not visual.is_file() or visual.stat().st_size < 200:
        issues.append("缺少 视觉蓝图.md 或内容过短")
    elif visual.is_file():
        visual_text = visual.read_text(encoding="utf-8", errors="replace")
        issues.extend(_verify_visual_blueprint_depth(visual_text, spec_text))

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
                issues.extend(_verify_visual_lock_depth(data, h5_shell=h5))
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
) -> tuple[bool, list[str]]:
    """V3 Phase 1 gate: PM+UI+Plan merged deliverables."""
    ok_pm, issues_pm = verify_phase1_pm_outputs(
        workspace,
        tool_flutter=tool_flutter,
        videostream=videostream,
        h5_shell=h5_shell,
        csv_full_name=csv_full_name,
    )
    ok_ui, issues_ui = verify_phase2_designer_outputs(workspace)
    issues = list(issues_pm) + list(issues_ui)

    from batch.uupm_design_system import find_design_system_master

    master = find_design_system_master(workspace, app_name)
    if master is None or master.stat().st_size < 200:
        issues.append("缺少 design-system MASTER.md（design.system 步骤产物）")
    pointer = workspace / "设计系统建议.md"
    if not pointer.is_file():
        issues.append("缺少 设计系统建议.md（skill.design 指针文件）")
    adapt_brief = workspace / "skill-adapt" / "design-brief.md"
    if not adapt_brief.is_file():
        issues.append("缺少 skill-adapt/design-brief.md（skill.adapt 产物）")

    for name, min_size in (
        ("产包计划.md", 300),
        ("资源计划.md", 150),
    ):
        path = workspace / name
        if not path.is_file() or path.stat().st_size < min_size:
            issues.append(f"缺少 {name} 或内容过短")

    plan = workspace / "产包计划.md"
    if plan.is_file():
        text = plan.read_text(encoding="utf-8", errors="replace")
        for marker in ("§1", "§2", "§3", "§4", "§5"):
            if marker not in text:
                issues.append(f"产包计划.md 缺少 {marker} 章节标记")
        if _plan_repeats_sdk_lock(text):
            issues.append("产包计划.md 不应重复锁定 flutter/dart SDK（已由 pubspec / 批次规范锁定）")
        if _plan_has_per_step_checkpoints(text):
            issues.append("产包计划.md §3 应为 Final Gate，禁止每步验收/analyze checkpoint")
        from batch.component_kit_index import verify_plan_component_order

        issues.extend(verify_plan_component_order(text))
        if "§3" in text and not re.search(
            r"final\s+gate|flutter\s+analyze|max_analyze_fix_rounds|0\s+.*error",
            text,
            re.I,
        ):
            issues.append("产包计划.md §3 应描述 Final Gate（flutter analyze 0 error + max_analyze_fix_rounds）")

    spec = workspace / "功能文档.md"
    if spec.is_file():
        spec_text = spec.read_text(encoding="utf-8", errors="replace")
        if "Data Contract" not in spec_text and "数据契约" not in spec_text:
            issues.append("功能文档.md 缺少 Data Contract / 数据契约 章节")

    from batch.selection_gate import verify_selection_plan

    issues.extend(
        verify_selection_plan(
            workspace,
            pack_type="h5_shell" if h5_shell else (
                "tool_flutter" if tool_flutter else (
                    "videostream" if videostream else "contentpack"
                )
            ),
            h5_shell=h5_shell,
        )
    )

    return (len(issues) == 0, issues)
