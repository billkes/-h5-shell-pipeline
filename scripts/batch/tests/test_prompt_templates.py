"""Ensure h5_shell prompt templates referenced by PromptBuilder exist."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROMPTS = ROOT / "prompts" / "h5_shell"

# Files loaded via PromptBuilder._load() for the default h5_shell pipeline.
REQUIRED_H5_SHELL_PROMPTS = [
    "_global_brain_block.txt",
    "phase_h5_shell_block.txt",
    "phase_h5_shell_programmer_block.txt",
    "phase_h5_kit_block.txt",
    "phase_h5_shell_programmer.txt",
    "phase_h5_shell_swift_programmer.txt",
    "phase_h5_shell_oc_programmer.txt",
    "phase_h5_implementer.txt",
    "phase_pm_ui_plan.txt",
]


def test_h5_shell_prompt_templates_exist() -> None:
    missing = [name for name in REQUIRED_H5_SHELL_PROMPTS if not (PROMPTS / name).is_file()]
    assert not missing, f"Missing prompt templates under {PROMPTS}: {missing}"


def test_h5_kit_block_substitution() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from batch.config import BatchConfig
    from batch.prompts import PromptBuilder

    pb = PromptBuilder(BatchConfig.from_env())
    block = pb.h5_kit_block(kit_deck_block="kitAtomSet: tap/type/mark")
    assert "kitAtomSet: tap/type/mark" in block
    assert "${H5_KIT_DECK_BLOCK}" not in block
