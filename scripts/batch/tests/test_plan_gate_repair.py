"""Tests for plan.gate repair target selection."""

from __future__ import annotations

from batch.plan_gate_repair import pick_repair_target, pick_soft_repair_target


def test_soft_prefers_flow_over_spec() -> None:
    soft = [
        "[SPEC-004] Primary Workflow 步骤不足",
        "[FLOW-001] 仍命中 legacy CRUD 模板",
    ]
    target = pick_soft_repair_target(soft)
    assert target is not None
    assert target.issue.startswith("[FLOW-")


def test_hard_missing_spec_file() -> None:
    target = pick_repair_target(
        hard=["缺少 功能文档.md 或内容过短"],
        soft=[],
    )
    assert target is not None
    assert target.category == "hard"
    assert "功能文档.md" in target.target_files
