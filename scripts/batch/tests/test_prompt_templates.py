"""Ensure h5_shell prompt templates referenced by PromptBuilder exist."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROMPTS = ROOT / "prompts" / "h5_shell"

REQUIRED_H5_SHELL_PROMPTS = [
    "phase_h5_shell_programmer.txt",
    "phase_h5_implementer.txt",
    "phase_agent_plan_spec.txt",
    "phase_agent_plan_pack.txt",
    "phase_plan_gate_repair.txt",
    "phase_h5_build_repair.txt",
]


def test_h5_shell_prompt_templates_exist() -> None:
    missing = [name for name in REQUIRED_H5_SHELL_PROMPTS if not (PROMPTS / name).is_file()]
    assert not missing, f"Missing prompt templates under {PROMPTS}: {missing}"


def test_v3_plan_spec_prompt_lists_merged_deliverables() -> None:
    text = (PROMPTS / "phase_agent_plan_spec.txt").read_text(encoding="utf-8")
    assert "${desc}" in text
    assert "${CSV_FULL_NAME}" in text
    assert "功能文档.md" in text
    assert "Privacy Agreement.md" in text
    assert "User Agreement.md" in text
    assert "产品概述" in text
    assert "Do **not** write `{CSV_FULL_NAME}.md`" in text
    assert "skill-input/agent-spec-index.md" in text


def test_product_doc_format_excludes_removed_sections() -> None:
    root = ROOT / "docs" / "H5壳产品文档格式.md"
    text = root.read_text(encoding="utf-8")
    assert "#### 产品概述" in text
    assert "#### App Store Listing" in text
    assert "已移除" in text
    assert "Listing 节之后文档结束" in text
    assert "功能文档.md" in text
    template_start = text.index("## 模板")
    template_end = text.index("**Listing 节之后文档结束。**")
    template = text[template_start:template_end]
    assert "Business Flow Summary" not in template
    assert "演示路线" not in template


def test_v3_plan_pack_prompt_no_visual_blueprint() -> None:
    text = (PROMPTS / "phase_agent_plan_pack.txt").read_text(encoding="utf-8")
    assert "本包登记信息.json" in text
    assert "本包视觉锁.json" in text
    assert "Do **not** write `视觉蓝图.md`" in text
    assert "Deliverables (write both JSON" in text


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
    assert "stack-vue.md" in text
    assert "stack-html-tailwind.md" in text
    assert "@phosphor-icons/vue" in text
    assert "tailwindcss" in text
    # Visual depth hard rules must appear BEFORE Required Reading (front-loaded).
    assert "### Visual Depth — Welcome + Tab1" in text
    assert text.index("### Visual Depth — Welcome + Tab1") < text.index(
        "### Required Reading"
    )
    assert "Welcome to {AppName}" in text
    assert "contextual greeting" in text.lower() or "Contextual greeting" in text


def test_global_brain_block_removed() -> None:
    assert not (PROMPTS / "_global_brain_block.txt").is_file()
