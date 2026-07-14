"""Tests for single build.agent step per package."""

from __future__ import annotations

from batch.pipeline_steps import (
    AGENT_STEPS,
    BUILD_AGENT,
    agent_steps_for_run,
    parse_step_range,
    steps_for_run,
)


def test_one_agent_step_for_tool_flutter() -> None:
    steps = steps_for_run(pack_type="tool_flutter")
    assert steps.count(BUILD_AGENT) == 1
    assert agent_steps_for_run(pack_type="tool_flutter") == (BUILD_AGENT,)
    assert BUILD_AGENT in AGENT_STEPS
    assert not any(s.startswith("audit.") for s in steps)


def test_one_agent_step_for_h5_shell() -> None:
    from batch.pipeline_steps import PREVIEW_TABS

    steps = steps_for_run(pack_type="h5_shell")
    assert steps.count(BUILD_AGENT) == 1
    assert agent_steps_for_run(pack_type="h5_shell") == (PREVIEW_TABS, BUILD_AGENT)
    assert "agent.plan" not in steps
    assert "agent.impl" not in steps
    assert not any(s.startswith("audit.") for s in steps)


def test_legacy_agent_ids_map_to_build_agent() -> None:
    steps = steps_for_run(pack_type="tool_flutter")
    for legacy in ("agent.plan", "agent.impl", "agent.shell", "agent.h5", "plan.agent"):
        assert parse_step_range(legacy, steps) == [BUILD_AGENT]
