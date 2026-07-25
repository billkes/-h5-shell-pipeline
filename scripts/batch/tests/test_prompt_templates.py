"""Ensure h5_shell prompt templates referenced by PromptBuilder exist."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROMPTS = ROOT / "prompts" / "h5_shell"

REQUIRED_H5_SHELL_PROMPTS = [
    "phase_h5_shell_programmer.txt",
    "phase_h5_implementer.txt",
    "phase_agent_design.txt",
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
    assert "skill-input/agent-workspace-focus.md" in text
    assert "法律协议规范.md" in text
    assert "docs/法律协议规范.md" not in text
    assert "`.cursor/rules/*.mdc` · `docs/rules/`" not in text
    assert "global-brain" not in text
    assert "paths under this workspace root" in text
    assert "outside the app root are out of scope" in text


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


def test_v3_design_prompt_owns_uiux_audit() -> None:
    text = (PROMPTS / "phase_agent_design.txt").read_text(encoding="utf-8")
    assert "design-audit.md" in text
    assert "H5壳ui-ux-pro-max使用规范.md" in text
    assert "SaaS" in text
    assert "Do **not** write `功能文档.md`" in text
    assert ".cursor/skills/ui-ux-pro-max/scripts/search.py" in text
    assert "--design-system --persist" in text
    assert "design owner" in text.lower() or "Design owner" in text


def test_v3_plan_pack_prompt_no_visual_blueprint() -> None:
    text = (PROMPTS / "phase_agent_plan_pack.txt").read_text(encoding="utf-8")
    assert "本包登记信息.json" in text
    assert "本包视觉锁.json" in text
    assert "Do **not** write `视觉蓝图.md`" in text
    assert "Deliverables (write both JSON" in text
    assert "design-audit.md" in text
    assert "agent.design" in text
    assert "re-run ui-ux-pro-max" in text or "do **not** re-run" in text.lower()


def test_v3_shell_prompt_is_runtime_unified() -> None:
    text = (PROMPTS / "phase_h5_shell_programmer.txt").read_text(encoding="utf-8")
    assert "${SHELL_RUNTIME}" in text
    assert "Deep Naming" in text
    assert "bridgeDeckSelections" in text
    assert "${H5_SHELL_BLOCK}" not in text
    assert "Launch & shell rasters" in text
    assert "1125×2436" in text or "1125x2436" in text.lower() or "1125" in text
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
    assert "H5壳ui-ux-pro-max使用规范.md" in text
    assert "Two-phase" in text
    assert "_preview/pages" in text
    assert "FREEZE.md" in text
    # Two-phase workflow + Surface depth before Required Reading.
    assert "### Two-phase workflow" in text
    assert "### Surface Depth — must-have surfaces" in text
    assert text.index("### Two-phase workflow") < text.index(
        "### Surface Depth — must-have surfaces"
    )
    assert text.index("### Surface Depth — must-have surfaces") < text.index(
        "### Required Reading"
    )
    assert "Welcome to {AppName}" in text
    assert "contextual greeting" in text.lower() or "Contextual greeting" in text
    assert "**Store**" in text
    assert "**Me / Settings**" in text
    assert "**Primary Workflow / Export" in text
    assert "**Other tab-roots**" in text
    assert "**Splash**" in text
    assert "hard-coded export" in text or "Forbid hard-coded export" in text
    assert "Safe area" in text or "safe area" in text.lower()
    assert "Anti-clone" in text or "batch-skeleton" in text
    assert "visually differentiated" in text or "isomorphic" in text
    assert "h5/public" in text
    assert "legalLinks" in text or "isExternalLegalUrl" in text
    assert "openExternalUrl" in text
    # Explicitly not front-loading Legal/Plaza polish in Surface Depth block.
    front = text.split("### Required Reading")[0]
    assert "**Legal**" not in front
    assert "**Plaza**" not in front


def test_global_brain_block_removed() -> None:
    assert not (PROMPTS / "_global_brain_block.txt").is_file()
