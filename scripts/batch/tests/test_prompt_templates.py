"""Ensure h5_shell prompt templates referenced by PromptBuilder exist."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROMPTS = ROOT / "prompts" / "h5_shell"

REQUIRED_H5_SHELL_PROMPTS = [
    "phase_h5_shell_programmer.txt",
    "phase_h5_implementer.txt",
    "phase_pm_ui_plan.txt",
    "phase_plan_gate_repair.txt",
    "phase_h5_build_repair.txt",
]


def test_h5_shell_prompt_templates_exist() -> None:
    missing = [name for name in REQUIRED_H5_SHELL_PROMPTS if not (PROMPTS / name).is_file()]
    assert not missing, f"Missing prompt templates under {PROMPTS}: {missing}"


def test_v3_plan_prompt_lists_deliverables() -> None:
    text = (PROMPTS / "phase_pm_ui_plan.txt").read_text(encoding="utf-8")
    assert "${desc}" in text
    assert "功能文档.md" in text
    assert "skill-input/agent-spec-index.md" in text
    assert "${DESIGN_SYSTEM_BLOCK}" not in text


def test_v3_shell_prompt_is_runtime_unified() -> None:
    text = (PROMPTS / "phase_h5_shell_programmer.txt").read_text(encoding="utf-8")
    assert "${SHELL_RUNTIME}" in text
    assert "${H5_SHELL_BLOCK}" not in text
    assert not (PROMPTS / "phase_h5_shell_swift_programmer.txt").is_file()
    assert not (PROMPTS / "phase_h5_shell_oc_programmer.txt").is_file()


def test_v3_h5_prompt_has_no_block_injection() -> None:
    text = (PROMPTS / "phase_h5_implementer.txt").read_text(encoding="utf-8")
    assert "${H5_SHELL_BLOCK}" not in text
    assert "${PAGE_OVERRIDES_BLOCK}" not in text
    assert "skill-input/agent-spec-index.md" in text
    assert "${desc}" in text


def test_global_brain_block_removed() -> None:
    assert not (PROMPTS / "_global_brain_block.txt").is_file()
