"""H5 shell 功能文档 business depth tier resolution and plan.gate checks."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

_L3_PATTERN = re.compile(
    r"stat|analytic|report|compare|trend|dashboard|insight|forecast|同比|环比|报表",
    re.I,
)
_L2_PATTERN = re.compile(
    r"budget|remind|inventory|control|ledger|track|spend|expense|planner|"
    r"预算|提醒|采购|到期|库存|管控|记账",
    re.I,
)
_BR_PATTERN = re.compile(r"\bBR-0*(\d+)\b", re.I)
_OPTIONAL_PATTERN = re.compile(
    r"\b(?:optional|may\s+be\s+skipped|if\s+needed|can\s+be\s+skipped)\b|可选项|可选",
    re.I,
)


def _strip_glossary_for_optional_scan(spec_text: str) -> str:
    """Remove Domain Glossary — field definitions may use 'Optional' as a qualifier."""
    match = re.search(
        r"(?is)(?:^|\n)#+\s*.*(?:domain\s+glossary|术语表).*?\n(.*?)(?:\n#+\s|\Z)",
        spec_text,
    )
    if not match:
        return spec_text
    return spec_text[: match.start()] + spec_text[match.end() :]


def _has_forbidden_optional_wording(spec_text: str) -> bool:
    scan_text = _strip_glossary_for_optional_scan(spec_text)
    return bool(_OPTIONAL_PATTERN.search(scan_text))
_WORKFLOW_STEP_PATTERN = re.compile(r"^\s*\d+[.)]\s+\S", re.M)
_GLOSSARY_ROW_PATTERN = re.compile(r"^\s*\|[^|]+\|[^|]+\|", re.M)
_SECONDARY_FLOW_PATTERN = re.compile(
    r"(?im)^#+\s*.*secondary\s+workflow|^#{0,3}\s*(?:flow\s+)?[A-Z]\s*[：:—-]",
)


@dataclass(frozen=True)
class BusinessDepthTier:
    tier_id: str
    label: str
    min_entities: int
    min_rules: int
    min_primary_steps: int
    min_secondary_flows: int
    min_secondary_steps: int
    min_glossary: int
    min_metrics: int
    min_spec_chars: int


TIER_SPECS: dict[str, BusinessDepthTier] = {
    "L1": BusinessDepthTier("L1", "record", 3, 5, 10, 1, 6, 6, 0, 2500),
    "L2": BusinessDepthTier("L2", "control", 3, 7, 12, 2, 6, 8, 1, 3500),
    "L3": BusinessDepthTier("L3", "analytics", 4, 9, 14, 2, 8, 10, 2, 4500),
}

_SECTION_CHECKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Domain Model", ("domain model", "data contract", "数据契约")),
    ("Business Rules", ("business rules", "rules engine")),
    ("Primary Workflow", ("primary workflow", "main tool flow")),
    ("Secondary Workflow", ("secondary workflow",)),
    ("State & Empty Matrix", ("state & empty", "state and empty", "empty matrix")),
    ("Professional Surface", ("professional surface", "domain glossary", "glossary")),
    ("4.2 Native Offset", ("4.2 native offset", "native offset")),
    ("Bridge Capability", ("bridge capability", "bridge matrix")),
    ("Screen Inventory", ("screen inventory",)),
    ("Export / Save", ("export", "save flow")),
    ("IAP & Free Tier", ("iap catalog", "free tier")),
    ("H5 Architecture", ("h5 architecture",)),
)


def spec_depth_gate_enabled() -> bool:
    return os.environ.get("ENABLE_SPEC_DEPTH_GATE", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def resolve_business_depth_tier(
    *,
    core_scene: str = "",
    local_feature: str = "",
    product_flow: str = "",
    theme_angle: str = "",
    explicit: str = "",
) -> str:
    """Infer L1/L2/L3 from CSV product fields; default L2 for h5_shell."""
    tier = (explicit or "").strip().upper()
    if tier in TIER_SPECS:
        return tier
    blob = " ".join(
        filter(None, (core_scene, local_feature, product_flow, theme_angle))
    )
    if _L3_PATTERN.search(blob):
        return "L3"
    if _L2_PATTERN.search(blob):
        return "L2"
    return "L2"


def resolve_tier_from_workspace(workspace: Path) -> str:
    ctx_path = workspace / "skill-input" / "context.json"
    if not ctx_path.is_file():
        return "L2"
    try:
        ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "L2"
    if not isinstance(ctx, dict):
        return "L2"
    constraints = ctx.get("constraints") or {}
    if isinstance(constraints, dict):
        explicit = str(constraints.get("businessDepthTier") or "").strip().upper()
        if explicit in TIER_SPECS:
            return explicit
    product = ctx.get("product") or {}
    if not isinstance(product, dict):
        return "L2"
    return resolve_business_depth_tier(
        core_scene=str(product.get("coreScene") or ""),
        local_feature=str(product.get("localFeature") or ""),
        product_flow=str(product.get("productFlow") or product.get("themeAngle") or ""),
        theme_angle=str(product.get("themeAngle") or ""),
    )


def tier_spec(tier_id: str) -> BusinessDepthTier:
    return TIER_SPECS.get(tier_id.upper(), TIER_SPECS["L2"])


def _section_present(text: str, fragments: tuple[str, ...]) -> bool:
    lower = text.lower()
    for frag in fragments:
        f = frag.lower()
        if f in lower:
            return True
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            if f in stripped.lower():
                return True
    return False


def _extract_section(text: str, fragments: tuple[str, ...]) -> str:
    lines = text.splitlines()
    start: int | None = None
    start_level = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        title = stripped[level:].strip().lower()
        if any(f in title for f in fragments):
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


def _count_entities(domain_section: str) -> int:
    rows = [
        ln
        for ln in re.findall(r"^\s*\|[^|]+\|", domain_section, re.M)
        if not re.match(r"^\s*\|[-: ]+\|", ln)
    ]
    if len(rows) >= 2:
        return max(0, len(rows) - 1)
    bullets = re.findall(r"^\s*(?:[-*]|\d+[.)])\s+\*?\*?[A-Z][a-zA-Z]+", domain_section, re.M)
    return len(bullets)


def _count_glossary_entries(text: str) -> int:
    section = _extract_section(text, ("domain glossary", "professional surface", "glossary"))
    if not section:
        return 0
    rows = [
        ln
        for ln in re.findall(r"^\s*\|[^|]+\|", section, re.M)
        if not re.match(r"^\s*\|[-: ]+\|", ln)
        and "term" not in ln.lower()
    ]
    if len(rows) >= 2:
        return max(0, len(rows) - 1)
    return len(re.findall(r"^\s*(?:[-*]|\d+[.)])\s+\S", section, re.M))


def _count_metrics(text: str) -> int:
    section = _extract_section(text, ("metrics", "reports", "export"))
    hits = len(
        re.findall(
            r"metric|indicator|kpi|口径|weekly|monthly|summary\s+card",
            section,
            re.I,
        )
    )
    if hits >= 2:
        return max(1, hits // 2)
    return 1 if re.search(r"metrics?\s*&\s*reports?", text, re.I) else 0


def _count_secondary_flows(text: str) -> int:
    section = _extract_section(text, ("secondary workflow",))
    if not section.strip():
        return 0
    headings = len(re.findall(r"^#{1,4}\s+", section, re.M))
    flow_labels = len(_SECONDARY_FLOW_PATTERN.findall(section))
    steps = len(_WORKFLOW_STEP_PATTERN.findall(section))
    if flow_labels >= 2:
        return flow_labels
    if headings >= 2:
        return headings
    return 1 if steps >= 6 else 0


def _signature_binds_workflow(text: str) -> bool:
    sig = _extract_section(text, ("signature", "h5 interaction"))
    if not sig.strip():
        blob = text
    else:
        blob = sig
    return bool(
        re.search(r"step\s+\d+|workflow\s+step|primary\s+workflow|BR-\d+", blob, re.I)
    )


def verify_spec_business_depth(
    spec_text: str,
    *,
    tier_id: str = "L2",
) -> list[str]:
    """Return plan.gate issue strings for 功能文档.md business depth."""
    if not spec_text.strip():
        return ["[SPEC-000] 功能文档.md 为空"]

    tier = tier_spec(tier_id)
    issues: list[str] = []

    if len(spec_text) < tier.min_spec_chars:
        issues.append(
            f"[SPEC-001] 功能文档过短（{len(spec_text)} 字符，"
            f"{tier.tier_id} 要求 ≥{tier.min_spec_chars}）"
        )

    for label, frags in _SECTION_CHECKS:
        if not _section_present(spec_text, frags):
            issues.append(f"[SPEC-002] 功能文档.md 缺少章节: {label}")

    br_section = _extract_section(spec_text, ("business rules", "rules engine"))
    br_count = len(_BR_PATTERN.findall(br_section or spec_text))
    if br_count < tier.min_rules:
        issues.append(
            f"[SPEC-003] Business Rules 不足（BR-xx 仅 {br_count} 条，"
            f"{tier.tier_id} 要求 ≥{tier.min_rules}）"
        )

    primary = _extract_section(spec_text, ("primary workflow", "main tool flow"))
    primary_steps = len(_WORKFLOW_STEP_PATTERN.findall(primary))
    if primary_steps < tier.min_primary_steps:
        issues.append(
            f"[SPEC-004] Primary Workflow 步骤不足（{primary_steps} 步，"
            f"{tier.tier_id} 要求 ≥{tier.min_primary_steps}）"
        )

    secondary_flows = _count_secondary_flows(spec_text)
    if secondary_flows < tier.min_secondary_flows:
        issues.append(
            f"[SPEC-005] Secondary Workflows 不足（{secondary_flows} 条，"
            f"{tier.tier_id} 要求 ≥{tier.min_secondary_flows}）"
        )

    glossary = _count_glossary_entries(spec_text)
    if glossary < tier.min_glossary:
        issues.append(
            f"[SPEC-006] Domain Glossary 不足（约 {glossary} 条，"
            f"{tier.tier_id} 要求 ≥{tier.min_glossary}）"
        )

    metrics = _count_metrics(spec_text)
    if metrics < tier.min_metrics:
        issues.append(
            f"[SPEC-007] Metrics & Reports 不足（{metrics} 项，"
            f"{tier.tier_id} 要求 ≥{tier.min_metrics}）"
        )

    domain = _extract_section(spec_text, ("domain model", "data contract"))
    entities = _count_entities(domain)
    if entities < tier.min_entities:
        issues.append(
            f"[SPEC-008] Domain Model 实体不足（约 {entities} 个，"
            f"{tier.tier_id} 要求 ≥{tier.min_entities}）"
        )

    native = _extract_section(spec_text, ("4.2 native offset", "native offset"))
    native_bullets = len(re.findall(r"^\s*(?:[-*]|\d+[.)]|^\s*\|)", native, re.M))
    if native_bullets < 3:
        issues.append("[SPEC-009] 4.2 Native Offset 须 ≥3 项")

    if re.search(r"signature", spec_text, re.I) and not _signature_binds_workflow(spec_text):
        issues.append(
            "[SPEC-010] signature H5 interaction 须绑定 Primary Workflow 步骤或 BR-xx"
        )

    if _has_forbidden_optional_wording(spec_text):
        issues.append("[SPEC-011] 功能文档禁止 optional/may/可选项 等模糊措辞")

    return issues


def format_business_depth_block(workspace: Path) -> str:
    """Prompt block injected at build.agent Part 1."""
    tier_id = resolve_tier_from_workspace(workspace)
    tier = tier_spec(tier_id)
    lines = [
        "[Business Depth — MANDATORY for 功能文档.md (plan.gate SPEC-xxx)]",
        f"- Tier: **{tier.tier_id}** ({tier.label}) — see 《H5壳功能文档深度标准.md》",
        f"- Min length: {tier.min_spec_chars} chars",
        f"- Domain entities: ≥{tier.min_entities}",
        f"- Business rules BR-01…: ≥{tier.min_rules}",
        f"- Primary Workflow numbered steps: ≥{tier.min_primary_steps}",
        f"- Secondary Workflows: ≥{tier.min_secondary_flows} (each ≥{tier.min_secondary_steps} steps)",
        f"- Domain Glossary terms: ≥{tier.min_glossary}",
        f"- Metrics & Reports definitions: ≥{tier.min_metrics}",
        "- Sections (English, in order): Domain Model · Business Rules · Primary Workflow ·",
        "  Secondary Workflows · State & Empty Matrix · Professional Surface ·",
        "  4.2 Native Offset · Bridge Capability Matrix · Screen Inventory ·",
        "  Export/Save · IAP & Free Tier · §H5 Architecture",
        "- signature H5 interaction MUST cite a Primary Workflow step (not decorative-only).",
        "- FORBIDDEN: optional / may / 可选项 — every listed item is MUST implement.",
        "- Complexity stays in H5 domain logic + Bridge; NO login / cloud sync / native Tabs.",
    ]
    return "\n".join(lines)
