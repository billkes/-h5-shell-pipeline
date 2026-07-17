"""Tests for V3 granular agent step split (plan / shell / h5)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

from batch.pipeline_steps import (  # noqa: E402
    AGENT_H5,
    AGENT_PLAN,
    AGENT_SHELL,
    AGENT_STEPS,
    BUILD_AGENT,
    agent_steps_for_run,
    parse_step_range,
    steps_for_run,
)


def test_granular_agent_steps_for_h5_shell() -> None:
    steps = steps_for_run(pack_type="h5_swift_shell")
    assert AGENT_PLAN in steps
    assert AGENT_SHELL in steps
    assert AGENT_H5 in steps
    # 顺序: plan < shell < h5
    assert steps.index(AGENT_PLAN) < steps.index(AGENT_SHELL)
    assert steps.index(AGENT_SHELL) < steps.index(AGENT_H5)
    # build.agent 不在新流水线步骤序列中
    assert BUILD_AGENT not in steps
    # agent_steps_for_run 返回三个拆分步骤
    assert agent_steps_for_run(pack_type="h5_swift_shell") == (
        AGENT_PLAN,
        AGENT_SHELL,
        AGENT_H5,
    )
    assert AGENT_STEPS == (AGENT_PLAN, AGENT_SHELL, AGENT_H5)
    # 不应有 audit.* 残留
    assert not any(s.startswith("audit.") for s in steps)


def test_granular_agent_steps_for_h5_oc_shell() -> None:
    steps = steps_for_run(pack_type="h5_oc_shell")
    assert AGENT_PLAN in steps
    assert AGENT_SHELL in steps
    assert AGENT_H5 in steps
    assert BUILD_AGENT not in steps


def test_legacy_build_agent_maps_to_agent_plan() -> None:
    """CLI 输入 'build.agent' / 'plan.agent' / 'dev.agent' 映射到 agent.plan。"""
    steps = steps_for_run(pack_type="h5_swift_shell")
    for legacy in ("build.agent", "plan.agent", "dev.agent"):
        assert parse_step_range(legacy, steps) == [AGENT_PLAN], legacy
    # agent.shell / agent.h5 各自映射
    assert parse_step_range("agent.shell", steps) == [AGENT_SHELL]
    assert parse_step_range("agent.h5", steps) == [AGENT_H5]


def test_non_h5_shell_has_no_agent_steps() -> None:
    """新流水线只支持 h5_shell;非 h5_shell 包没有 agent 步骤。"""
    steps = steps_for_run(pack_type="tool_flutter")
    assert BUILD_AGENT not in steps
    assert AGENT_PLAN not in steps
    assert AGENT_SHELL not in steps
    assert AGENT_H5 not in steps
    assert agent_steps_for_run(pack_type="tool_flutter") == ()