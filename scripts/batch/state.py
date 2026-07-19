"""Per-app build state (.build-state.json) management.

Pipeline V3 — two macro phases, granular ``steps`` for breakpoint resume:

* plan.* — lock dimensions, Agent blueprint, gate, git
* dev.* — pub get, analyze, native check, git

Macro phase keys (``phase_pm_ui_plan`` / ``phase_programmer``) are derived from ``steps`` for reports.

Pipeline V2 (``--legacy-pipeline``) — four roles:

* phase_pm / phase_ui / phase_programmer / phase_tester

Legacy keys (phase1 … phase10) are read for resume compatibility only.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from batch.batch_log import log_detail

STATE_FILE = ".build-state.json"
STEPS_KEY = "steps"
PHASE_COUNT = 3

PIPELINE_V3 = "v3"
PIPELINE_V2 = "v2"

# V3 phases
PM_UI_PLAN_PHASE = "phase_pm_ui_plan"
ASSETS_PHASE = "phase_assets"
PROGRAMMER_PHASE = "phase_programmer"

V3_PHASES = (
    PM_UI_PLAN_PHASE,
    PROGRAMMER_PHASE,
)

# Legacy V2 phases (aliases kept for imports)
PM_PHASE = "phase_pm"
UI_PHASE = "phase_ui"
TEST_PHASE = "phase_tester"

LEGACY_PHASES = (
    PM_PHASE,
    UI_PHASE,
    PROGRAMMER_PHASE,
    TEST_PHASE,
)

# Default export: V3
PHASES = V3_PHASES

PHASE_LABELS: dict[str, str] = {
    PM_UI_PLAN_PHASE: "PM+UI+Plan · 蓝图与计划",
    PROGRAMMER_PHASE: "Programmer · 实现 + analyze",
    ASSETS_PHASE: "Assets · 成品配图",
    PM_PHASE: "PM · 功能蓝图",
    UI_PHASE: "UI · 视觉蓝图",
    TEST_PHASE: "Tester · Main Tool Flow",
}

PHASE_SHORT: dict[str, str] = {
    PM_UI_PLAN_PHASE: "Plan",
    PROGRAMMER_PHASE: "Dev",
    ASSETS_PHASE: "Assets",
    PM_PHASE: "PM",
    UI_PHASE: "UI",
    TEST_PHASE: "Test",
}

# Backward-compatible aliases used by older modules/tests.
HEALTH_PHASE = PROGRAMMER_PHASE
FINAL_PHASE = PROGRAMMER_PHASE
REVIEW_PHASE = PROGRAMMER_PHASE
ASSET_PHASE = ASSETS_PHASE

_LEGACY_PM = "phase1"
_LEGACY_UI = "phase2"
_LEGACY_IMPL = "phase4"
_LEGACY_HEALTH = "phase6"
_LEGACY_TEST = "phase7"


def pipeline_version_from_data(data: dict[str, Any]) -> str:
    """Return ``v3`` or ``v2`` from state dict."""
    ver = str(data.get("pipeline_version") or "").strip().lower()
    if ver in (PIPELINE_V3, PIPELINE_V2):
        return ver
    if PM_UI_PLAN_PHASE in data or "phase_auditor" in data:
        return PIPELINE_V3
    if PM_PHASE in data or UI_PHASE in data or TEST_PHASE in data:
        return PIPELINE_V2
    return PIPELINE_V3


def phases_for_version(version: str) -> tuple[str, ...]:
    return LEGACY_PHASES if version == PIPELINE_V2 else V3_PHASES


def phases_for_workspace(workspace: Path) -> tuple[str, ...]:
    return phases_for_version(pipeline_version_from_data(read_state(workspace)))


def final_phase_for_version(version: str) -> str:
    if version == PIPELINE_V2:
        return TEST_PHASE
    return PROGRAMMER_PHASE


def pipeline_complete(workspace: Path) -> bool:
    """True when the pipeline reached its terminal phase for this version."""
    data = read_state(workspace)
    ver = pipeline_version_from_data(data)
    final = final_phase_for_version(ver)
    return phase_status_from_data(data, final) == "done"


def _aggregate_phase_status(step_statuses: list[str]) -> str:
    if not step_statuses:
        return "pending"
    if all(s == "done" for s in step_statuses):
        return "done"
    if any(s == "failed" for s in step_statuses):
        return "failed"
    if any(s == "running" for s in step_statuses):
        return "running"
    if all(s in ("done", "skipped") for s in step_statuses):
        return "done"
    if any(s == "done" for s in step_statuses):
        return "running"
    if all(s == "skipped" for s in step_statuses):
        return "skipped"
    return "pending"


def sync_phases_from_steps(data: dict[str, Any]) -> None:
    """Derive macro phase keys from granular ``steps`` dict."""
    from batch.pipeline_steps import PHASE_STEPS, steps_for_run

    steps_map = data.get(STEPS_KEY)
    if not isinstance(steps_map, dict) or not steps_map:
        return
    pack_type = str(data.get("pack_type") or "contentpack")
    ordered = steps_for_run(pack_type=pack_type)
    migrated = steps_map_from_data(data)
    for phase, phase_steps in PHASE_STEPS.items():
        statuses = [str(migrated.get(s) or "pending") for s in phase_steps if s in ordered]
        if statuses:
            data[phase] = _aggregate_phase_status(statuses)


def _infer_steps_from_phases(data: dict[str, Any]) -> dict[str, str]:
    """Best-effort migration when ``steps`` missing (old .build-state.json)."""
    from batch.pipeline_steps import (
        ANALYZE,
        BUILD_AGENT,
        LOCK_DIMENSIONS,
        PREPARE_CONTEXT,
        PREVIEW_TABS,
        SKILL_ADAPT,
        SKILL_DESIGN,
        GIT_DEV,
        GIT_PLAN,
        PLAN_GATE,
        PUBGET,
        steps_for_run,
    )

    _plan_prep = (
        PREPARE_CONTEXT,
        SKILL_DESIGN,
        SKILL_ADAPT,
        LOCK_DIMENSIONS,
        PREVIEW_TABS,
        BUILD_AGENT,
        PLAN_GATE,
        GIT_PLAN,
    )

    pack_type = str(data.get("pack_type") or "contentpack")
    ordered = steps_for_run(pack_type=pack_type)
    steps: dict[str, str] = {s: "pending" for s in ordered}

    plan = _phase_status_legacy(data, PM_UI_PLAN_PHASE)
    if plan == "done":
        for s in _plan_prep:
            if s in steps:
                steps[s] = "done"
    elif plan == "failed":
        for s in _plan_prep:
            if s in steps:
                steps[s] = "done" if s != PLAN_GATE else "failed"
                break

    dev = _phase_status_legacy(data, PROGRAMMER_PHASE)
    agent_sub = str(data.get("phase_programmer_agent") or "pending")
    h5_sub = str(data.get("phase_h5_agent") or "pending")
    if dev == "done":
        for s in (PUBGET, ANALYZE, GIT_DEV):
            if s in steps:
                steps[s] = "done"
        for s in _plan_prep[:6]:
            if s in steps:
                steps[s] = "done"
        if BUILD_AGENT in steps:
            steps[BUILD_AGENT] = "done"
    elif agent_sub == "done" or h5_sub == "done":
        for s in _plan_prep[:4]:
            if s in steps:
                steps[s] = "done"
        if BUILD_AGENT in steps:
            steps[BUILD_AGENT] = "done"
    elif dev == "failed":
        for s in (PUBGET, ANALYZE):
            if s in steps and steps[s] == "pending":
                steps[s] = "failed"
                break

    audit_legacy = str(data.get("phase_auditor") or "pending")
    if audit_legacy == "done" and dev != "done":
        for s in (PUBGET, ANALYZE, GIT_DEV):
            if s in steps:
                steps[s] = "done"

    return steps


def _aggregate_legacy_agent_steps(steps: dict[str, str]) -> dict[str, str]:
    """Collapse truly-legacy agent step ids (agent.impl, plan.agent, dev.agent, dev.h5) into build.agent.

    Note: ``agent.plan`` / ``agent.shell`` / ``agent.h5`` are V3 first-class
    steps (not legacy) and are preserved as-is. Only ``agent.impl`` and the
    older role aliases get aggregated, since V3 no longer exposes ``agent.impl``
    as a runnable step (non-h5_shell packs fall back to single ``build.agent``).
    """
    from batch.pipeline_steps import (
        AGENT_IMPL,
        BUILD_AGENT,
        DEV_AGENT,
        DEV_H5,
        PLAN_AGENT,
    )

    out = dict(steps)
    legacy = (AGENT_IMPL, PLAN_AGENT, DEV_AGENT, DEV_H5)
    if not any(s in out for s in legacy):
        return out
    if out.get(BUILD_AGENT) in ("done", "failed", "running"):
        for s in legacy:
            out.pop(s, None)
        return out

    required = [s for s in legacy if s in out]
    statuses = [out.get(s, "pending") for s in required]
    if any(s == "failed" for s in statuses):
        out[BUILD_AGENT] = "failed"
    elif all(s == "done" for s in statuses):
        out[BUILD_AGENT] = "done"
    elif any(s == "done" for s in statuses):
        out[BUILD_AGENT] = "failed"
    for s in legacy:
        out.pop(s, None)
    return out


def _collapse_agent_plan_docs(steps: dict[str, str]) -> dict[str, str]:
    """Merge legacy ``agent.plan.docs`` into ``agent.plan.spec``."""
    from batch.pipeline_steps import AGENT_PLAN_DOCS, AGENT_PLAN_SPEC

    terminal = frozenset({"done", "skipped", "failed"})
    out = dict(steps)
    docs_status = out.pop(AGENT_PLAN_DOCS, None)
    if docs_status is None:
        return out
    spec_status = out.get(AGENT_PLAN_SPEC, "pending")
    if spec_status in terminal and docs_status in terminal:
        out[AGENT_PLAN_SPEC] = "done" if spec_status == "done" and docs_status == "done" else spec_status
    elif spec_status == "pending":
        out[AGENT_PLAN_SPEC] = docs_status
    elif docs_status == "failed" and spec_status not in ("failed", "done"):
        out[AGENT_PLAN_SPEC] = "failed"
    return out


def _expand_legacy_plan_agent(steps: dict[str, str]) -> dict[str, str]:
    """Map legacy ``agent.plan`` onto ``agent.plan.spec/pack``."""
    from batch.pipeline_steps import AGENT_PLAN, PLAN_AGENT_STEPS

    out = _collapse_agent_plan_docs(steps)
    legacy_status = out.pop(AGENT_PLAN, None)
    if not legacy_status:
        return out
    if legacy_status == "done":
        for s in PLAN_AGENT_STEPS:
            if s not in out:
                out[s] = "done"
    elif legacy_status in ("failed", "running"):
        if PLAN_AGENT_STEPS[0] not in out:
            out[PLAN_AGENT_STEPS[0]] = legacy_status
        for s in PLAN_AGENT_STEPS[1:]:
            if s not in out:
                out[s] = "pending"
    return out


def _expand_build_agent_to_granular(steps: dict[str, str]) -> dict[str, str]:
    """Expand legacy ``build.agent`` status into granular plan/shell/h5 steps."""
    from batch.pipeline_steps import AGENT_H5, AGENT_SHELL, BUILD_AGENT, PLAN_AGENT_STEPS

    out = _expand_legacy_plan_agent(steps)
    legacy_status = out.get(BUILD_AGENT)
    if not legacy_status:
        return out

    if legacy_status == "done":
        for s in (*PLAN_AGENT_STEPS, AGENT_SHELL, AGENT_H5):
            if s not in out:
                out[s] = "done"
    elif legacy_status in ("failed", "running"):
        if PLAN_AGENT_STEPS[0] not in out:
            out[PLAN_AGENT_STEPS[0]] = legacy_status
        for s in (*PLAN_AGENT_STEPS[1:], AGENT_SHELL, AGENT_H5):
            if s not in out:
                out[s] = "pending"
    return out


_TERMINAL_STEP = frozenset({"done", "skipped", "failed"})


def _promote_to_done(out: dict[str, str], step_id: str) -> None:
    """Upgrade pending/running (or missing) step to done; keep terminal states."""
    if out.get(step_id) not in _TERMINAL_STEP:
        out[step_id] = "done"


def _backfill_prep_chain_when_build_done(out: dict[str, str], chain: tuple[str, ...]) -> None:
    """V3 single-agent: build.agent done implies prep/skill chain ran."""
    from batch.pipeline_steps import BUILD_AGENT

    if out.get(BUILD_AGENT) != "done":
        return
    for step_id in chain:
        _promote_to_done(out, step_id)


def _migrate_legacy_step_keys(steps: dict[str, str]) -> dict[str, str]:
    """Map removed step ids onto the single-agent pipeline."""
    from batch.pipeline_steps import (
        ANALYZE,
        BUILD_AGENT,
        LOCK_DIMENSIONS,
        PREPARE_CONTEXT,
        PREVIEW_TABS,
        SKILL_ADAPT,
        SKILL_DESIGN,
        SKILL_ENRICH,
        SKILL_PAGES,
        SKILL_TOKENS,
        GIT_DEV,
        GIT_PLAN,
        PUBGET,
        _REMOVED_STEP_IDS,
    )

    out = _aggregate_legacy_agent_steps(dict(steps))
    _skill_chain = (
        PREPARE_CONTEXT,
        SKILL_DESIGN,
        SKILL_ENRICH,
        SKILL_ADAPT,
        SKILL_PAGES,
        SKILL_TOKENS,
        LOCK_DIMENSIONS,
    )
    _backfill_prep_chain_when_build_done(out, _skill_chain)
    _backfill_prep_chain_when_build_done(out, (PREVIEW_TABS,))
    # Legacy step ids
    if out.get("prepare") == "done" or out.get("prepare.context") == "done":
        _promote_to_done(out, PREPARE_CONTEXT)
    if out.get("design.system") == "done" or out.get("skill.design") == "done":
        _promote_to_done(out, SKILL_DESIGN)
        _promote_to_done(out, PREPARE_CONTEXT)
    if out.get("skill.adapt") == "done":
        _promote_to_done(out, SKILL_ADAPT)
    if out.get("skill.enrich") == "done":
        _promote_to_done(out, SKILL_ENRICH)
    if out.get("skill.pages") == "done":
        _promote_to_done(out, SKILL_PAGES)
    if out.get("skill.tokens") == "done":
        _promote_to_done(out, SKILL_TOKENS)
    if out.get("lock.dimensions") == "done":
        _promote_to_done(out, LOCK_DIMENSIONS)
    if out.get("preview.tabs") == "done":
        _promote_to_done(out, PREVIEW_TABS)
    if out.get("plan.agent") == "done":
        _promote_to_done(out, BUILD_AGENT)
    if out.get("dev.agent") == "done" or out.get("dev.h5") == "done":
        _promote_to_done(out, BUILD_AGENT)
    legacy_done = (
        out.get("plan.agent") == "done"
        or out.get("dev.agent") == "done"
        or out.get("dev.h5") == "done"
    )
    if legacy_done and out.get(BUILD_AGENT, "pending") == "pending":
        out[BUILD_AGENT] = "done"
    if out.get("plan.prepare") == "done" or out.get("dev.prepare") == "done":
        _promote_to_done(out, PREPARE_CONTEXT)
    if out.get("plan.git") == "done":
        _promote_to_done(out, GIT_PLAN)
    if out.get("dev.pubget") == "done":
        _promote_to_done(out, PUBGET)
    if out.get("dev.analyze") == "done":
        _promote_to_done(out, ANALYZE)
    if out.get("dev.fix") == "done":
        _promote_to_done(out, ANALYZE)
    if out.get("dev.git") == "done":
        _promote_to_done(out, GIT_DEV)
    for old in (
        "plan.agent",
        "dev.agent",
        "dev.fix",
        "dev.h5",
        "audit.agent",
        "plan.prepare",
        "dev.prepare",
        "plan.git",
        "dev.git",
        *_REMOVED_STEP_IDS,
    ):
        out.pop(old, None)
    aggregated = _aggregate_legacy_agent_steps(out)
    expanded = _expand_build_agent_to_granular(aggregated)
    return _expand_legacy_plan_agent(expanded)


def steps_map_from_data(data: dict[str, Any]) -> dict[str, str]:
    from batch.pipeline_steps import steps_for_run

    raw = data.get(STEPS_KEY)
    if isinstance(raw, dict) and raw:
        migrated = _migrate_legacy_step_keys({str(k): str(v) for k, v in raw.items()})
        ordered = steps_for_run(
            pack_type=str(data.get("pack_type") or "h5_swift_shell"),
        )
        return {s: migrated.get(s, "pending") for s in ordered} | {
            k: v for k, v in migrated.items() if k not in ordered
        }
    return _infer_steps_from_phases(data)


def get_step(workspace: Path, step_id: str) -> str:
    data = read_state(workspace)
    return steps_map_from_data(data).get(step_id, "pending")


def step_done(workspace: Path, step_id: str) -> bool:
    return get_step(workspace, step_id) == "done"


def set_step(
    workspace: Path,
    step_id: str,
    value: str,
    *,
    sync_phases: bool = True,
    **extra: Any,
) -> None:
    sf = workspace / STATE_FILE
    data: dict[str, Any] = read_state(workspace) if sf.is_file() else {}
    now = datetime.now()
    steps = steps_map_from_data(data)
    steps[step_id] = value
    if step_id == "build.agent" and value == "done":
        from batch.pipeline_steps import (
            LOCK_DIMENSIONS,
            PREPARE_CONTEXT,
            PREVIEW_TABS,
            SKILL_ADAPT,
            SKILL_DESIGN,
            SKILL_ENRICH,
            SKILL_PAGES,
            SKILL_TOKENS,
        )

        for prep_step in (
            PREPARE_CONTEXT,
            SKILL_DESIGN,
            SKILL_ENRICH,
            SKILL_ADAPT,
            SKILL_PAGES,
            SKILL_TOKENS,
            LOCK_DIMENSIONS,
            PREVIEW_TABS,
        ):
            if steps.get(prep_step) not in _TERMINAL_STEP:
                steps[prep_step] = "done"
    data[STEPS_KEY] = steps
    data["updated_at"] = now.isoformat()
    start_key = f"step_{step_id.replace('.', '_')}_started_at"
    if value == "running":
        data[start_key] = now.isoformat()
    elif value in ("done", "failed", "skipped") and start_key in data:
        try:
            started = datetime.fromisoformat(data[start_key])
            dur_key = f"step_{step_id.replace('.', '_')}_duration_s"
            data[dur_key] = int((now - started).total_seconds())
        except ValueError:
            pass
    for key, val in extra.items():
        try:
            data[key] = int(val)
        except (TypeError, ValueError):
            data[key] = val
    if sync_phases:
        sync_phases_from_steps(data)
    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def reset_steps(workspace: Path, step_ids: list[str]) -> None:
    for step_id in step_ids:
        set_step(workspace, step_id, "pending")


def first_incomplete_step(workspace: Path, ordered_steps: tuple[str, ...]) -> str | None:
    steps = steps_map_from_data(read_state(workspace))
    for step_id in ordered_steps:
        status = steps.get(step_id, "pending")
        if status in ("pending", "failed", "running"):
            return step_id
    return None


def first_failed_step(workspace: Path, ordered_steps: tuple[str, ...]) -> str | None:
    steps = steps_map_from_data(read_state(workspace))
    for step_id in ordered_steps:
        if steps.get(step_id) == "failed":
            return step_id
    return None


def phase_status_from_data(data: dict[str, Any], phase: str) -> str:
    """Resolve phase status from state dict, including legacy 10-phase keys."""
    if not data:
        return "pending"
    steps_map = data.get(STEPS_KEY)
    if isinstance(steps_map, dict) and steps_map:
        from batch.pipeline_steps import PHASE_STEPS, steps_for_run

        pack_type = str(data.get("pack_type") or "contentpack")
        ordered = steps_for_run(pack_type=pack_type)
        phase_steps = PHASE_STEPS.get(phase, ())
        migrated = steps_map_from_data(data)
        statuses = [
            str(migrated.get(s) or "pending")
            for s in phase_steps
            if s in ordered
        ]
        if statuses:
            return _aggregate_phase_status(statuses)

    return _phase_status_legacy(data, phase)


def _phase_status_legacy(data: dict[str, Any], phase: str) -> str:
    """Legacy phase resolution when ``steps`` dict is absent."""
    if not data:
        return "pending"
    direct = data.get(phase)
    if direct is not None and str(direct) != "pending":
        return str(direct)

    if phase == PM_UI_PLAN_PHASE:
        if data.get(PM_UI_PLAN_PHASE) == "done":
            return "done"
        pm = str(data.get(PM_PHASE) or data.get(_LEGACY_PM) or "pending")
        ui = str(data.get(UI_PHASE) or data.get(_LEGACY_UI) or "pending")
        if pm == "done" and ui == "done":
            return "done"
        if pm == "failed" or ui == "failed":
            return "failed"
        if pm == "running" or ui == "running":
            return "running"
        return str(data.get(PM_UI_PLAN_PHASE) or "pending")

    if phase == PM_PHASE:
        return str(data.get(_LEGACY_PM, data.get(PM_PHASE, "pending")))
    if phase == UI_PHASE:
        return str(data.get(_LEGACY_UI, data.get(UI_PHASE, "pending")))

    if phase == PROGRAMMER_PHASE:
        legacy_health = data.get(_LEGACY_HEALTH)
        if legacy_health is not None and str(legacy_health) != "pending":
            return str(legacy_health)
        legacy_impl = data.get(_LEGACY_IMPL)
        if legacy_impl in ("failed", "running", "skipped"):
            return str(legacy_impl)
        if legacy_impl == "done":
            return "pending"
        return str(data.get(PROGRAMMER_PHASE) or "pending")

    if phase == ASSETS_PHASE:
        if ASSETS_PHASE in data:
            return str(data.get(ASSETS_PHASE) or "pending")
        if _phase_status_legacy(data, PROGRAMMER_PHASE) == "done":
            return "done"
        return "pending"

    if phase == TEST_PHASE:
        return str(data.get(_LEGACY_TEST, data.get(TEST_PHASE, "pending")))

    return str(direct or "pending")


def init_state(
    workspace: Path,
    name: str,
    desc: str,
    dart_name: str,
    *,
    force: bool = False,
    pipeline_version: str = PIPELINE_V3,
    pack_type: str = "h5_swift_shell",
) -> bool:
    """Initialize state file. Returns True if created fresh."""
    sf = workspace / STATE_FILE
    if sf.is_file() and not force:
        log_detail("发现断点状态文件，将从上次中断处继续")
        return False
    phases = phases_for_version(pipeline_version)
    from batch.pipeline_steps import steps_for_run

    state: dict[str, Any] = {
        "name": name,
        "desc": desc,
        "dart_name": dart_name,
        "pipeline_version": pipeline_version,
        "pack_type": pack_type,
        "started_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        **{p: "pending" for p in phases},
    }
    if pipeline_version == PIPELINE_V3:
        step_ids = steps_for_run(pack_type=pack_type)
        state[STEPS_KEY] = {s: "pending" for s in step_ids}
    sf.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    if force:
        print(">>> --force 模式：重置状态，从头开始")
    else:
        print(">>> 状态文件已初始化")
    return True


def read_state(workspace: Path) -> dict[str, Any]:
    """Load build state dict; empty if missing or invalid."""
    sf = workspace / STATE_FILE
    if not sf.is_file():
        return {}
    try:
        data = json.loads(sf.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def update_state_fields(workspace: Path, **fields: Any) -> None:
    """Merge arbitrary fields into .build-state.json without changing phases."""
    sf = workspace / STATE_FILE
    data = read_state(workspace)
    now = datetime.now().isoformat()
    data["updated_at"] = now
    for key, val in fields.items():
        try:
            data[key] = int(val)
        except (TypeError, ValueError):
            data[key] = val
    if STEPS_KEY in fields or isinstance(data.get(STEPS_KEY), dict):
        sync_phases_from_steps(data)
    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_phase(workspace: Path, phase: str) -> str:
    return phase_status_from_data(read_state(workspace), phase)


def phase_done(workspace: Path, phase: str) -> bool:
    return get_phase(workspace, phase) == "done"


def set_phase(
    workspace: Path,
    phase: str,
    value: str,
    **extra: Any,
) -> None:
    sf = workspace / STATE_FILE
    data: dict[str, Any] = {}
    if sf.is_file():
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    now = datetime.now()
    data[phase] = value
    data["updated_at"] = now.isoformat()
    start_key = f"{phase}_started_at"
    if value == "running":
        data[start_key] = now.isoformat()
    elif value in ("done", "failed", "skipped") and start_key in data:
        try:
            started = datetime.fromisoformat(data[start_key])
            data[f"{phase}_duration_s"] = int((now - started).total_seconds())
        except ValueError:
            pass
    for key, val in extra.items():
        try:
            data[key] = int(val)
        except (TypeError, ValueError):
            data[key] = val

    # Keep granular ``steps`` in sync when callers still use the macro-phase API.
    if pipeline_version_from_data(data) == PIPELINE_V3:
        from batch.pipeline_steps import PHASE_STEPS, steps_for_run

        pack_type = str(data.get("pack_type") or "contentpack")
        ordered = steps_for_run(pack_type=pack_type)
        phase_steps = PHASE_STEPS.get(phase)
        if phase_steps:
            steps = dict(data.get(STEPS_KEY) or {})
            phase_step_set = {s for s in phase_steps if s in ordered}
            if value == "done":
                for s in phase_step_set:
                    steps[s] = "done"
            elif value == "skipped":
                for s in phase_step_set:
                    steps[s] = "skipped"
            elif value == "running":
                for s in phase_step_set:
                    if steps.get(s, "pending") == "pending":
                        steps[s] = "running"
                        break
            elif value == "failed":
                for s in phase_step_set:
                    if steps.get(s, "pending") != "done":
                        steps[s] = "failed"
                        break
            if phase_step_set:
                data[STEPS_KEY] = steps

    sf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def show_state(workspace: Path) -> None:
    sf = workspace / STATE_FILE
    if not sf.is_file():
        return
    from batch.batch_run_log import compact_resume_summary, get_run_log
    from batch.pipeline_steps import step_display, steps_for_run

    log = get_run_log()
    log.queue(compact_resume_summary(workspace))

    icons = {
        "done": "✅",
        "failed": "❌",
        "running": "⚡",
        "skipped": "⏭️",
    }
    data = read_state(workspace)
    if pipeline_version_from_data(data) == PIPELINE_V3:
        pack_type = str(data.get("pack_type") or "contentpack")
        ordered = steps_for_run(pack_type=pack_type)
        steps_map = steps_map_from_data(data)
        for step_id in ordered:
            status = steps_map.get(step_id, "pending")
            if status == "pending":
                continue
            icon = icons.get(status, "❓")
            suffix = " （将重试）" if status in ("failed", "running") else ""
            log.detail(f"  {icon} {step_display(step_id)}{suffix}")
        return

    for phase in phases_for_workspace(workspace):
        status = get_phase(workspace, phase)
        if status == "pending":
            continue
        icon = icons.get(status, "❓")
        label = PHASE_LABELS.get(phase, phase)
        suffix = " （将重试）" if status in ("failed", "running") else ""
        log.detail(f"  {icon} {label}{suffix}")
