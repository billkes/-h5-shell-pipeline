"""Tests for V3 granular agent step split (plan spec/docs/pack / shell / h5)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

from batch.pipeline_steps import (  # noqa: E402
    AGENT_H5,
    AGENT_PLAN_DOCS,
    AGENT_PLAN_PACK,
    AGENT_PLAN_SPEC,
    AGENT_SHELL,
    AGENT_STEPS,
    BUILD_AGENT,
    PLAN_AGENT_STEPS,
    agent_steps_for_run,
    parse_step_range,
    steps_for_run,
)


def test_granular_agent_steps_for_h5_shell() -> None:
    steps = steps_for_run(pack_type="h5_swift_shell")
    assert AGENT_PLAN_SPEC in steps
    assert AGENT_PLAN_DOCS in steps
    assert AGENT_PLAN_PACK in steps
    assert AGENT_SHELL in steps
    assert AGENT_H5 in steps
    assert steps.index(AGENT_PLAN_SPEC) < steps.index(AGENT_PLAN_DOCS)
    assert steps.index(AGENT_PLAN_DOCS) < steps.index(AGENT_PLAN_PACK)
    assert steps.index(AGENT_PLAN_PACK) < steps.index(AGENT_SHELL)
    assert steps.index(AGENT_SHELL) < steps.index(AGENT_H5)
    assert BUILD_AGENT not in steps
    assert agent_steps_for_run(pack_type="h5_swift_shell") == (
        *PLAN_AGENT_STEPS,
        AGENT_SHELL,
        AGENT_H5,
    )
    assert AGENT_STEPS == (*PLAN_AGENT_STEPS, AGENT_SHELL, AGENT_H5)


def test_granular_agent_steps_for_h5_oc_shell() -> None:
    steps = steps_for_run(pack_type="h5_oc_shell")
    assert AGENT_PLAN_SPEC in steps
    assert AGENT_PLAN_DOCS in steps
    assert AGENT_PLAN_PACK in steps
    assert BUILD_AGENT not in steps


def test_legacy_build_agent_maps_to_agent_plan_spec() -> None:
    steps = steps_for_run(pack_type="h5_swift_shell")
    for legacy in ("build.agent", "plan.agent", "dev.agent", "agent.plan"):
        assert parse_step_range(legacy, steps) == [AGENT_PLAN_SPEC], legacy
    assert parse_step_range("agent.plan.docs", steps) == [AGENT_PLAN_DOCS]
    assert parse_step_range("agent.plan.pack", steps) == [AGENT_PLAN_PACK]
    assert parse_step_range("agent.shell", steps) == [AGENT_SHELL]
    assert parse_step_range("agent.h5", steps) == [AGENT_H5]


def test_non_h5_shell_has_no_agent_steps() -> None:
    steps = steps_for_run(pack_type="tool_flutter")
    assert BUILD_AGENT not in steps
    assert AGENT_PLAN_SPEC not in steps
    assert AGENT_PLAN_DOCS not in steps
    assert AGENT_PLAN_PACK not in steps
    assert AGENT_SHELL not in steps
    assert AGENT_H5 not in steps
    assert agent_steps_for_run(pack_type="tool_flutter") == ()
