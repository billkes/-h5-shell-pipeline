"""Tests for V3 granular agent step split (plan spec/pack / shell / h5)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

from batch.pipeline_steps import (  # noqa: E402
    AGENT_DESIGN,
    AGENT_H5,
    AGENT_PLAN_DOCS,
    AGENT_PLAN_PACK,
    AGENT_PLAN_SPEC,
    AGENT_SHELL,
    AGENT_STEPS,
    BUILD_AGENT,
    LOCK_DIMENSIONS,
    PLAN_AGENT_STEPS,
    SYNC_DISTILLED,
    agent_steps_for_run,
    parse_step_range,
    steps_for_run,
)


def test_granular_agent_steps_for_h5_shell() -> None:
    steps = steps_for_run(pack_type="h5_swift_shell")
    assert AGENT_DESIGN in steps
    assert AGENT_PLAN_SPEC in steps
    assert AGENT_PLAN_DOCS not in steps
    assert AGENT_PLAN_PACK in steps
    assert AGENT_SHELL in steps
    assert AGENT_H5 in steps
    assert SYNC_DISTILLED in steps
    assert steps.index(LOCK_DIMENSIONS) < steps.index(SYNC_DISTILLED)
    assert steps.index(SYNC_DISTILLED) < steps.index(AGENT_DESIGN)
    assert steps.index(AGENT_DESIGN) < steps.index(AGENT_PLAN_SPEC)
    assert steps.index(AGENT_PLAN_SPEC) < steps.index(AGENT_PLAN_PACK)
    assert steps.index(AGENT_PLAN_PACK) < steps.index(AGENT_SHELL)
    assert steps.index(AGENT_SHELL) < steps.index(AGENT_H5)
    assert BUILD_AGENT not in steps
    assert agent_steps_for_run(pack_type="h5_swift_shell") == (
        *PLAN_AGENT_STEPS,
        AGENT_SHELL,
        AGENT_H5,
    )
    assert AGENT_STEPS == (*PLAN_AGENT_STEPS, AGENT_SHELL, AGENT_H5)
    assert PLAN_AGENT_STEPS == (AGENT_DESIGN, AGENT_PLAN_SPEC, AGENT_PLAN_PACK)
    # 1–7 = through lock; 8 = sync.distilled; 9 = agent.design
    assert steps[6] == LOCK_DIMENSIONS
    assert steps[7] == SYNC_DISTILLED
    assert steps[8] == AGENT_DESIGN
    assert steps[9] == AGENT_PLAN_SPEC


def test_granular_agent_steps_for_oc_shell() -> None:
    steps = steps_for_run(pack_type="h5_oc_shell")
    assert AGENT_PLAN_SPEC in steps
    assert AGENT_PLAN_DOCS not in steps
    assert AGENT_PLAN_PACK in steps


def test_legacy_build_agent_maps_to_agent_design() -> None:
    steps = steps_for_run(pack_type="h5_swift_shell")
    assert parse_step_range("build.agent", steps) == [AGENT_DESIGN]
    assert parse_step_range("agent.design", steps) == [AGENT_DESIGN]
    for legacy in ("plan.agent", "dev.agent", "agent.plan"):
        assert parse_step_range(legacy, steps) == [AGENT_PLAN_SPEC], legacy
    assert parse_step_range("agent.plan.docs", steps) == [AGENT_PLAN_SPEC]
    assert parse_step_range("agent.plan.pack", steps) == [AGENT_PLAN_PACK]


def test_rerun_accepts_range_like_bare_input() -> None:
    steps = steps_for_run(pack_type="h5_swift_shell")
    bare = parse_step_range("1-7", steps)
    assert len(bare) == 7
    assert bare[-1] == LOCK_DIMENSIONS
    through_sync = parse_step_range("1-8", steps)
    assert len(through_sync) == 8
    assert through_sync[-1] == SYNC_DISTILLED
    assert parse_step_range("rerun 1-8", steps) == through_sync
    assert parse_step_range("rerun 1-7", steps) == bare
    assert parse_step_range("rerun 5", steps) == parse_step_range("5", steps)
    assert parse_step_range("rerun prepare.context", steps) == [steps[0]]
    assert parse_step_range("rerun sync.distilled", steps) == [SYNC_DISTILLED]
    assert parse_step_range("rerun build.agent", steps) == [AGENT_DESIGN]
    assert parse_step_range("rerun agent.design", steps) == [AGENT_DESIGN]


def test_non_h5_shell_has_no_agent_steps() -> None:
    steps = steps_for_run(pack_type="tool_flutter")
    assert AGENT_PLAN_SPEC not in steps
    assert AGENT_PLAN_DOCS not in steps
    assert AGENT_PLAN_PACK not in steps
    assert AGENT_SHELL not in steps
    assert AGENT_H5 not in steps
    assert SYNC_DISTILLED not in steps
