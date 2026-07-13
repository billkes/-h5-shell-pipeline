"""Self-composed theme brief parsing and task-ready narrative audit."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from batch.interaction_topology import recommend_topology_ids
from batch.task_schema import (
    COL_AUDIENCE,
    COL_CORE_SCENE,
    COL_LOCAL_FEATURE,
    COL_THEME_CN,
    COL_TRACK,
)

_NUMBER_PREFIX_RE = re.compile(r"^\s*\d+[.)]\s*")
_SPLIT_RE = re.compile(r"[：:]\s*")

_CRUD_MAIN_SELL_RE = re.compile(
    r"(?:pick\s+a\s+category\s+chip|chip\s+to\s+browse|browse\s+.*\s+list|"
    r"分类筛选|浏览列表|周报导出|list\s+management|列表管理|"
    r"save\s+entries\s+in\s+a\s+.*\s+log\s+notes)",
    re.I,
)
_GENERIC_LOCAL_RE = re.compile(
    r"^(?:记录本|日记|清单管理工具?|管理工具|日常记录|列表管理)$",
    re.I,
)
_GENERIC_SCENE_RE = re.compile(
    r"^(?:日常使用|管理|记录|产品记录|数据管理)$",
    re.I,
)
_PROFESSIONAL_ANCHOR_RE = re.compile(
    r"水质|补色|周期|掉色|WPM|语速|提词|佩戴|干涩|红血丝|"
    r"预算|到期|提醒|口味|评分|白名单|社交强度|回血|耗能|"
    r"关系|场景|礼物|边界|自测|presentation|reminder|budget|checklist",
    re.I,
)

_TRACK_RULES: tuple[tuple[str, str], ...] = (
    (r"染发|护色|发质|水质", "美妆个护"),
    (r"隐形|眼镜|镜片|佩戴|干涩", "健康个护"),
    (r"礼物|派对|生日|社交|边界", "轻社交"),
    (r"咖啡|点单|口味|咖啡馆", "餐饮生活"),
    (r"演讲|提词|课堂|presentation|语速", "校园效率"),
    (r"清单|自测|规划|档案|追踪|日记|记忆", "效率工具"),
)

_AUDIENCE_RULES: tuple[tuple[str, str], ...] = (
    (r"陪读|家长", "陪读家长"),
    (r"大学生|大学|presentation|课堂", "大学生"),
    (r"年轻人群|社交内耗", "年轻职场人"),
    (r"染发|发质", "染发人群"),
    (r"隐形眼镜|佩戴", "隐形眼镜用户"),
    (r"咖啡|点单", "咖啡常客"),
    (r"派对|生日|礼物", "派对筹备者"),
)

_SCENE_RULES: tuple[tuple[str, str], ...] = (
    (r"护色追踪|补色周期|掉色", "护色周期追踪"),
    (r"佩戴时长|适配|干涩", "镜片佩戴适配"),
    (r"点单记忆|口味评分|白名单", "咖啡馆点单记忆"),
    (r"提词|语速|presentation|演讲", "课堂演讲提词"),
    (r"礼物匹配|选礼", "礼物场景匹配"),
    (r"社交耗能|回血节奏|社交强度", "社交电量规划"),
    (r"亲密边界|自测清单", "亲密边界自测"),
)

_FEATURE_RULES: tuple[tuple[str, str], ...] = (
    (r"水质.*护色|护色方案", "水质匹配护色方案"),
    (r"补色周期|掉色速度", "补色周期档案"),
    (r"干涩|红血丝|适配款", "场景化镜片适配"),
    (r"口味评分|专属口味|点单白名单", "个人口味白名单"),
    (r"滚动提词|语速预警|超时段落", "语速预警提词"),
    (r"关系.*预算.*场景|小众平价礼物", "关系预算场景匹配"),
    (r"社交耗能|回血|社交强度", "社交强度建议"),
    (r"亲密边界|自测", "边界自测清单"),
)


@dataclass
class ThemeAuditResult:
    ok: bool
    codes: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    parsed: dict[str, str] = field(default_factory=dict)
    suggest_topology: list[str] = field(default_factory=list)

    def primary_code(self) -> str:
        return self.codes[0] if self.codes else ""


def _strip_number_prefix(text: str) -> str:
    return _NUMBER_PREFIX_RE.sub("", text.strip())


def parse_one_liner(text: str) -> dict[str, str]:
    """Parse a one-line theme brief into task.csv theme columns."""
    raw = _strip_number_prefix(text.strip())
    if not raw:
        return {}

    theme_cn = raw
    body = ""
    if _SPLIT_RE.search(raw):
        parts = _SPLIT_RE.split(raw, maxsplit=1)
        theme_cn = parts[0].strip()
        body = parts[1].strip() if len(parts) > 1 else ""

    blob = f"{theme_cn} {body}"
    track = _match_rule(blob, _TRACK_RULES) or "效率工具"
    audience = _match_rule(blob, _AUDIENCE_RULES) or _infer_audience(blob)
    core_scene = _match_rule(blob, _SCENE_RULES) or _infer_scene(theme_cn, body)
    local_feature = _match_rule(blob, _FEATURE_RULES) or _infer_feature(theme_cn, body)

    if len(theme_cn) > 40:
        theme_cn = theme_cn[:40].rstrip("，,、 ")

    return {
        COL_THEME_CN: theme_cn,
        COL_TRACK: track,
        COL_AUDIENCE: audience,
        COL_CORE_SCENE: core_scene,
        COL_LOCAL_FEATURE: local_feature,
    }


def _match_rule(blob: str, rules: tuple[tuple[str, str], ...]) -> str:
    for pattern, value in rules:
        if re.search(pattern, blob, re.I):
            return value
    return ""


def _infer_audience(blob: str) -> str:
    if re.search(r"用户|人群|群体", blob):
        m = re.search(r"([\u4e00-\u9fff]{2,8})(?:用户|人群)", blob)
        if m:
            return m.group(1)
    return "目标用户"


def _infer_scene(theme_cn: str, body: str) -> str:
    for token in re.split(r"[，,、\s]+", theme_cn):
        token = token.strip()
        if len(token) >= 4 and token not in ("追踪档案", "适配日记", "记忆库"):
            return token[:12]
    if body:
        m = re.search(r"记录([\u4e00-\u9fff]{2,10})", body)
        if m:
            return m.group(1)[:12]
    return theme_cn[:12] if theme_cn else "核心场景"


def _infer_feature(theme_cn: str, body: str) -> str:
    if body:
        m = re.search(
            r"(?:匹配|沉淀|建议|筛选|预警|追踪|记录|标记)([\u4e00-\u9fff]{2,12})",
            body,
        )
        if m:
            return m.group(0)[:16]
        clauses = re.split(r"[，,；;]", body)
        if len(clauses) >= 2:
            return clauses[1].strip()[:16]
    return theme_cn[-8:] if len(theme_cn) >= 4 else "差异化机制"


def audit_theme_brief(
    *,
    theme_cn: str = "",
    track: str = "",
    audience: str = "",
    core_scene: str = "",
    local_feature: str = "",
    product_flow: str = "",
    row_name: str = "",
    batch_dup_theme_cn: str = "",
    batch_dup_pair_owner: str = "",
) -> ThemeAuditResult:
    """Validate a single row's self-composed theme brief."""
    parsed = {
        COL_THEME_CN: theme_cn.strip(),
        COL_TRACK: track.strip(),
        COL_AUDIENCE: audience.strip(),
        COL_CORE_SCENE: core_scene.strip(),
        COL_LOCAL_FEATURE: local_feature.strip(),
    }
    codes: list[str] = []
    hints: list[str] = []
    blob = " ".join(parsed.values()) + f" {product_flow}"

    if not theme_cn.strip():
        codes.append("THEME-000")
        hints.append("填写中文主题（≤40 字产品定位）")
    elif len(theme_cn.strip()) > 40:
        codes.append("THEME-005")
        hints.append(f"中文主题压缩到 ≤40 字（当前 {len(theme_cn.strip())} 字）")
    elif theme_cn.strip().startswith("关于") and len(theme_cn.strip()) > 24:
        codes.append("THEME-005")
        hints.append("避免库式长句「关于…记录本」，改为一击即懂的产品名")

    if batch_dup_theme_cn:
        codes.append("THEME-001")
        hints.append(f"中文主题批内重复（与 {batch_dup_theme_cn} 冲突）")

    pair_key = f"{core_scene.strip()}|{local_feature.strip()}"
    if batch_dup_pair_owner and core_scene.strip() and local_feature.strip():
        codes.append("THEME-002")
        hints.append(
            f"核心场景+本地功能 二元组批内重复（与 {batch_dup_pair_owner} 相同：{pair_key}）"
        )

    if _CRUD_MAIN_SELL_RE.search(blob) or _CRUD_MAIN_SELL_RE.search(product_flow):
        codes.append("THEME-003")
        hints.append("主卖点勿用 chip 浏览/分类筛选/周报导出/列表管理 套话")
        hints.append("把差异化机制写进「本地功能」（如周期追踪、语速预警、水质方案）")

    if _GENERIC_LOCAL_RE.match(local_feature.strip()) or _GENERIC_SCENE_RE.match(
        core_scene.strip()
    ):
        codes.append("THEME-004")
        hints.append("避免泛化叙事：「记录本/日记/列表管理/日常使用」不能作主卖点")
        hints.append("加入 ≥1 个专业锚点（周期、WPM、水质、预算上限、口味白名单等）")

    if blob.strip() and not _PROFESSIONAL_ANCHOR_RE.search(blob):
        codes.append("THEME-004")
        hints.append("补充领域锚点词，让审核员 30 秒内能说清「这 App 做什么」")

    for label, val in (
        ("赛道分类", track),
        ("目标人群", audience),
        ("核心场景", core_scene),
        ("本地功能", local_feature),
    ):
        if theme_cn.strip() and not val.strip():
            codes.append("THEME-008")
            hints.append(f"补全 {label}（compose-theme 可自动解析）")

    suggest = recommend_topology_ids(
        core_scene=core_scene,
        local_feature=local_feature,
        theme_cn=theme_cn,
        extra=blob,
    )
    if "THEME-003" in codes and not suggest:
        suggest = ["T6_checklist_session", "T8_reminder_ring"]
    if codes and "THEME-003" in codes and suggest:
        hints.append(f"推荐 topology: {', '.join(suggest[:2])}")

    ok = not codes
    return ThemeAuditResult(
        ok=ok,
        codes=codes,
        hints=hints,
        parsed=parsed,
        suggest_topology=suggest,
    )


def audit_theme_rows(rows: list[Any]) -> list[tuple[int, str, ThemeAuditResult]]:
    """Audit all rows; return (1-based index, row name, result)."""
    theme_seen: dict[str, str] = {}
    pair_seen: dict[str, str] = {}
    out: list[tuple[int, str, ThemeAuditResult]] = []

    for idx, row in enumerate(rows, start=1):
        name = str(getattr(row, "name", "") or "").strip() or f"行{idx}"
        theme_cn = str(getattr(row, "theme_cn", "") or "").strip()
        if not theme_cn:
            continue

        dup_theme = ""
        if theme_cn in theme_seen and theme_seen[theme_cn] != name:
            dup_theme = theme_seen[theme_cn]
        else:
            theme_seen.setdefault(theme_cn, name)

        core = str(getattr(row, "core_scene", "") or "").strip()
        local = str(getattr(row, "local_feature", "") or "").strip()
        pair = f"{core}|{local}"
        dup_pair = ""
        if pair != "|" and pair in pair_seen and pair_seen[pair] != name:
            dup_pair = pair_seen[pair]
        else:
            pair_seen.setdefault(pair, name)

        product_flow = str(getattr(row, "product_flow", "") or "").strip()
        result = audit_theme_brief(
            theme_cn=theme_cn,
            track=str(getattr(row, "track", "") or ""),
            audience=str(getattr(row, "audience", "") or ""),
            core_scene=core,
            local_feature=local,
            product_flow=product_flow,
            row_name=name,
            batch_dup_theme_cn=dup_theme,
            batch_dup_pair_owner=dup_pair,
        )
        out.append((idx, name, result))
    return out


def format_theme_audit_failure(
    row_index: int,
    row_name: str,
    result: ThemeAuditResult,
    *,
    csv_path: str = "task.csv",
) -> str:
    """Human-readable block for task-ready / compose-theme."""
    code = result.primary_code() or "THEME-ERR"
    lines = [
        f"❌ 行 {row_index} — {row_name} — {code}",
        "",
        "当前解析:",
    ]
    for key, label in (
        (COL_THEME_CN, "中文主题"),
        (COL_TRACK, "赛道分类"),
        (COL_AUDIENCE, "目标人群"),
        (COL_CORE_SCENE, "核心场景"),
        (COL_LOCAL_FEATURE, "本地功能"),
    ):
        val = result.parsed.get(key, "")
        if val:
            lines.append(f"  {label}: {val}")
    if result.suggest_topology:
        lines.append(f"  推荐 topology: {', '.join(result.suggest_topology[:3])}")
    lines.append("")
    lines.append("调整推荐:")
    for i, hint in enumerate(result.hints[:6], start=1):
        lines.append(f"  {i}. {hint}")
    lines.extend(
        [
            "",
            "可继续:",
            f"  ./run.sh task-compose-theme --row {row_index} --text \"...\"",
            f"  或手改 {csv_path} 后 ./run.sh task-ready",
        ]
    )
    return "\n".join(lines)
