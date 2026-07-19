"""V3 pipeline granular step definitions — single Build Agent + script gates."""

from __future__ import annotations

from batch.pack_type import is_flutter_runtime, is_h5_shell
from batch.state import PM_UI_PLAN_PHASE, PROGRAMMER_PHASE

# ── Step IDs ──────────────────────────────────────────────────────────

PREPARE_CONTEXT = "prepare.context"
SKILL_DESIGN = "skill.design"
SKILL_ENRICH = "skill.enrich"
SKILL_ADAPT = "skill.adapt"
SKILL_PAGES = "skill.pages"
SKILL_TOKENS = "skill.tokens"
LOCK_DIMENSIONS = "lock.dimensions"
PREVIEW_TABS = "preview.tabs"

BUILD_AGENT = "build.agent"

# Legacy granular agent step ids (migration / CLI aliases only — not in V3_STEPS)
AGENT_PLAN = "agent.plan"
AGENT_IMPL = "agent.impl"
AGENT_SHELL = "agent.shell"
AGENT_H5 = "agent.h5"

# Legacy aliases
PREPARE = PREPARE_CONTEXT
DESIGN_SYSTEM = SKILL_DESIGN

PLAN_GATE = "plan.gate"
DEV_H5_BUILD = "dev.h5.build"
GIT_PLAN = "git.plan"
PUBGET = "dev.pubget"
ANALYZE = "dev.analyze"
GIT_DEV = "git.dev"

# Removed from V3_STEPS — kept only so migration can drop them from .build-state.json
_REMOVED_STEP_IDS: frozenset[str] = frozenset({"dev.h5.gate", "native.check"})

# Legacy ids (migration / tests only)
PLAN_PREPARE = PREPARE_CONTEXT
PLAN_AGENT = "plan.agent"
PLAN_GIT = GIT_PLAN
DEV_PREPARE = PREPARE_CONTEXT
DEV_AGENT = "dev.agent"
DEV_PUBGET = PUBGET
DEV_ANALYZE = ANALYZE
DEV_FIX = "dev.fix"
DEV_H5 = "dev.h5"
DEV_GIT = GIT_DEV

V3_STEPS: tuple[str, ...] = (
    PREPARE_CONTEXT,
    SKILL_DESIGN,
    SKILL_ENRICH,
    SKILL_ADAPT,
    SKILL_PAGES,
    SKILL_TOKENS,
    LOCK_DIMENSIONS,
    AGENT_PLAN,
    AGENT_SHELL,
    AGENT_H5,
    PLAN_GATE,
    DEV_H5_BUILD,
    GIT_PLAN,
    PUBGET,
    ANALYZE,
    GIT_DEV,
)

AGENT_STEPS: tuple[str, ...] = (AGENT_PLAN, AGENT_SHELL, AGENT_H5)

_LEGACY_AGENT_STEP_IDS: frozenset[str] = frozenset(
    {AGENT_IMPL, PLAN_AGENT, DEV_AGENT, DEV_H5}
)

STEP_LABELS: dict[str, str] = {
    PREPARE_CONTEXT: "skill-input · 事实与防撞上下文",
    SKILL_DESIGN: "ui-ux-pro-max · 设计系统生成",
    SKILL_ENRICH: "skill.enrich · 多域 UX/图标/H5 brief",
    SKILL_ADAPT: "skill-adapt · 候选选型与转换",
    SKILL_PAGES: "skill.pages · 逐屏 override",
    SKILL_TOKENS: "skill.tokens · 设计 Token 同步",
    LOCK_DIMENSIONS: "锁维度 + 工程准备",
    PREVIEW_TABS: "Tab 明暗预览 · 静态 HTML",
    BUILD_AGENT: "Build Agent · 蓝图 + 实现（legacy 单次调用）",
    AGENT_PLAN: "Agent · 蓝图与计划文档",
    AGENT_IMPL: "Agent · Flutter 实现（legacy）",
    AGENT_SHELL: "Agent · H5 原生壳",
    AGENT_H5: "Agent · H5 vault / legal",
    PLAN_GATE: "产出校验 + 主题登记",
    DEV_H5_BUILD: "Vite 编译修复 · h5 → h5_site（max 3 轮）",
    GIT_PLAN: "Git 提交（计划产物）",
    PUBGET: "flutter pub get",
    ANALYZE: "flutter analyze",
    GIT_DEV: "Git 提交（代码）",
}

STEP_TO_PHASE: dict[str, str] = {
    PREPARE_CONTEXT: PM_UI_PLAN_PHASE,
    SKILL_DESIGN: PM_UI_PLAN_PHASE,
    SKILL_ENRICH: PM_UI_PLAN_PHASE,
    SKILL_ADAPT: PM_UI_PLAN_PHASE,
    SKILL_PAGES: PM_UI_PLAN_PHASE,
    SKILL_TOKENS: PM_UI_PLAN_PHASE,
    LOCK_DIMENSIONS: PM_UI_PLAN_PHASE,
    PREVIEW_TABS: PM_UI_PLAN_PHASE,
    BUILD_AGENT: PM_UI_PLAN_PHASE,
    AGENT_PLAN: PM_UI_PLAN_PHASE,
    AGENT_SHELL: PM_UI_PLAN_PHASE,
    AGENT_H5: PM_UI_PLAN_PHASE,
    PLAN_GATE: PM_UI_PLAN_PHASE,
    DEV_H5_BUILD: PM_UI_PLAN_PHASE,
    GIT_PLAN: PM_UI_PLAN_PHASE,
    PUBGET: PROGRAMMER_PHASE,
    ANALYZE: PROGRAMMER_PHASE,
    GIT_DEV: PROGRAMMER_PHASE,
}

PHASE_STEPS: dict[str, tuple[str, ...]] = {
    PM_UI_PLAN_PHASE: (
        PREPARE_CONTEXT,
        SKILL_DESIGN,
        SKILL_ENRICH,
        SKILL_ADAPT,
        SKILL_PAGES,
        SKILL_TOKENS,
        LOCK_DIMENSIONS,
        AGENT_PLAN,
        AGENT_SHELL,
        AGENT_H5,
        PLAN_GATE,
        DEV_H5_BUILD,
        GIT_PLAN,
    ),
    PROGRAMMER_PHASE: (
        PUBGET,
        ANALYZE,
        GIT_DEV,
    ),
}


def steps_for_run(*, pack_type: str) -> tuple[str, ...]:
    """Return ordered step ids for this app + config.

    h5_shell packs run the granular three-step agent chain (plan/shell/h5).
    Non-h5_shell packs have no agent steps in V3 (the new pipeline only
    produces h5_shell packs; legacy single-call ``build.agent`` remains
    available via ``parse_step_range`` for manual debugging).
    """
    steps: list[str] = []
    is_h5 = is_h5_shell(pack_type)
    for step in V3_STEPS:
        if step == DEV_H5_BUILD and not is_h5:
            continue
        if step in (AGENT_PLAN, AGENT_SHELL, AGENT_H5) and not is_h5:
            continue
        if step in (PUBGET, ANALYZE) and not is_flutter_runtime(pack_type):
            continue
        steps.append(step)
    return tuple(steps)


def agent_steps_for_run(*, pack_type: str) -> tuple[str, ...]:
    ordered = steps_for_run(pack_type=pack_type)
    return tuple(s for s in ordered if s in AGENT_STEPS)


def step_display(step_id: str) -> str:
    """Single-line label for terminal / logs."""
    label = STEP_LABELS.get(step_id, step_id)
    return f"{step_id} · {label}"


def step_duration_key(step_id: str) -> str:
    return f"step_{step_id.replace('.', '_')}_duration_s"


def step_index(step_id: str, steps: tuple[str, ...]) -> int:
    try:
        return steps.index(step_id) + 1
    except ValueError:
        return 0


def parse_step_range(raw: str, steps: tuple[str, ...]) -> list[str]:
    """Parse ``7``, ``7-10``, or step id like ``dev.analyze``."""
    text = raw.strip().lower()
    if not text:
        return []
    if text in ("continue", "c", "续跑", "继续"):
        return []
    legacy_map = {
        "plan.prepare": PREPARE_CONTEXT,
        "dev.prepare": PREPARE_CONTEXT,
        "prepare": PREPARE_CONTEXT,
        "design.system": SKILL_DESIGN,
        "skill.design": SKILL_DESIGN,
        "skill.enrich": SKILL_ENRICH,
        "skill.adapt": SKILL_ADAPT,
        "skill.pages": SKILL_PAGES,
        "skill.tokens": SKILL_TOKENS,
        "lock.dimensions": LOCK_DIMENSIONS,
        "preview.tabs": PREVIEW_TABS,
        "build.agent": AGENT_PLAN,
        "plan.agent": AGENT_PLAN,
        "dev.agent": AGENT_PLAN,
        "agent.plan": AGENT_PLAN,
        "agent.impl": BUILD_AGENT,
        "agent.shell": AGENT_SHELL,
        "agent.h5": AGENT_H5,
        "dev.h5": AGENT_H5,
        "dev.fix": ANALYZE,
        "plan.git": GIT_PLAN,
        "dev.git": GIT_DEV,
        "dev.pubget": PUBGET,
        "dev.analyze": ANALYZE,
        "dev.h5.build": DEV_H5_BUILD,
    }
    if text in legacy_map:
        mapped = legacy_map[text]
        return [mapped] if mapped in steps else []
    by_id = {s: i for i, s in enumerate(steps)}
    if text in by_id:
        return [text]
    if text.startswith("rerun "):
        text = text[6:].strip()
        if text in legacy_map:
            text = legacy_map[text]
        if text in by_id:
            return [text]
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(steps):
                return [steps[idx]]
        return []
    if "-" in text:
        parts = text.split("-", 1)
        if all(p.isdigit() for p in parts):
            start = max(1, int(parts[0]))
            end = min(len(steps), int(parts[1]))
            if start <= end:
                return list(steps[start - 1 : end])
        return []
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(steps):
            return [steps[idx]]
    return []
