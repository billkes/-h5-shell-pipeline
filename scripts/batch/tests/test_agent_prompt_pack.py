"""Tests for post-lock.dimensions Agent prompt pack (5 filled prompts + runbook)."""

from __future__ import annotations

from pathlib import Path

from batch.agent_prompt_pack import (
    AGENT_PROMPTS_DIR,
    MAIN_AGENT_SLOTS,
    RUNBOOK_JSON_REL,
    RUNBOOK_MD_REL,
    WEB_AGENT_RESUME_MD_REL,
    write_agent_prompt_pack,
    write_web_agent_resume_handbook,
)
from batch.config import BatchConfig
from batch.pipeline_steps import (
    AGENT_DESIGN,
    AGENT_H5,
    AGENT_PLAN_PACK,
    AGENT_PLAN_SPEC,
    AGENT_SHELL,
)
from batch.prompts import PromptBuilder


def test_main_agent_slots_are_exactly_five() -> None:
    assert len(MAIN_AGENT_SLOTS) == 5
    assert [s.step_id for s in MAIN_AGENT_SLOTS] == [
        AGENT_DESIGN,
        AGENT_PLAN_SPEC,
        AGENT_PLAN_PACK,
        AGENT_SHELL,
        AGENT_H5,
    ]
    assert [s.seq for s in MAIN_AGENT_SLOTS] == [1, 2, 3, 4, 5]


def test_write_agent_prompt_pack_fills_five_prompts(tmp_path: Path) -> None:
    (tmp_path / "skill-input").mkdir()
    (tmp_path / "skill-input" / "context.json").write_text("{}", encoding="utf-8")

    cfg = BatchConfig.from_env()
    prompts = PromptBuilder(cfg)
    pack_context = {
        "name": "Lensoo",
        "desc": "Theme: contact lens diary",
        "dart_name": "lensoo",
        "prefix": "lnsoo",
        "product_req_doc": "H5壳Flutter产品要求.md",
        "p2_product_doc": "H5壳Flutter产品要求.md",
        "shell_runtime": "swift",
        "csv_full_name": "Lensoo",
    }

    runbook = write_agent_prompt_pack(
        tmp_path,
        prompts=prompts,
        pack_context=pack_context,
        app_name="Lensoo",
        pack_type="h5_swift_shell",
    )

    assert len(runbook["execution_order"]) == 5
    assert (tmp_path / RUNBOOK_MD_REL).is_file()
    assert (tmp_path / RUNBOOK_JSON_REL).is_file()

    for slot in MAIN_AGENT_SLOTS:
        prompt_path = tmp_path / AGENT_PROMPTS_DIR / f"{slot.seq:02d}-{slot.step_id}.md"
        assert prompt_path.is_file(), prompt_path
        text = prompt_path.read_text(encoding="utf-8")
        assert f"seq={slot.seq}" in text
        assert f"step={slot.step_id}" in text
        assert "Lensoo" in text
        assert "${name}" not in text
        assert "${desc}" not in text
        assert "${BRIDGE_CHANNEL}" not in text
        assert "${FLUTTER_DART_PREFIX}" not in text
        assert "${PRODUCT_REQ_DOC}" not in text
        assert "${P2_PRODUCT_DOC}" not in text
        assert "${SHELL_RUNTIME}" not in text
        assert "${CSV_FULL_NAME}" not in text
        assert "${RESUME_BLOCK}" not in text
        assert "${dart_name}" not in text

    prompt_files = sorted((tmp_path / AGENT_PROMPTS_DIR).glob("*"))
    assert len(prompt_files) == 5
    assert all(p.suffix == ".md" and p.name[0].isdigit() for p in prompt_files)

    md = (tmp_path / RUNBOOK_MD_REL).read_text(encoding="utf-8")
    assert "`agent.design`" in md
    assert "`agent.plan.spec`" in md
    assert "`agent.h5`" in md
    assert "01-agent.design.md" in md
    assert "02-agent.plan.spec.md" in md
    assert WEB_AGENT_RESUME_MD_REL in md
    assert "agent-spec-index" not in md
    assert "agent-brain-focus" not in md


def test_write_web_agent_resume_handbook_from_runbook(tmp_path: Path) -> None:
    (tmp_path / "skill-input").mkdir()
    (tmp_path / "skill-input" / "context.json").write_text("{}", encoding="utf-8")

    cfg = BatchConfig.from_env()
    prompts = PromptBuilder(cfg)
    pack_context = {
        "name": "Lensoo",
        "desc": "Theme: contact lens diary",
        "dart_name": "lensoo",
        "prefix": "teqxb",
        "product_req_doc": "H5壳Flutter产品要求.md",
        "p2_product_doc": "H5壳Flutter产品要求.md",
        "shell_runtime": "swift",
        "csv_full_name": "Lensoo",
    }
    write_agent_prompt_pack(
        tmp_path,
        prompts=prompts,
        pack_context=pack_context,
        app_name="Lensoo",
        pack_type="h5_swift_shell",
    )

    out = write_web_agent_resume_handbook(
        tmp_path,
        app_name="Lensoo",
        pack_type="h5_swift_shell",
        prefix="teqxb",
        shell_runtime="swift",
    )
    assert out == tmp_path / WEB_AGENT_RESUME_MD_REL
    text = out.read_text(encoding="utf-8")
    assert "网页 Agent 续跑手册 — Lensoo" in text
    assert "sync.distilled" in text
    assert "01-agent.design.md" in text
    assert "05-agent.h5.md" in text
    assert "agent.design" in text
    assert "lensooBridge" in text
    assert "lensooBridgeCallback" in text
    assert "teqxb" in text
    assert f"@{WEB_AGENT_RESUME_MD_REL}" in text


def test_write_web_agent_resume_handbook_without_runbook(tmp_path: Path) -> None:
    out = write_web_agent_resume_handbook(
        tmp_path,
        app_name="Buildioo",
        pack_type="h5_swift_shell",
        prefix="bldio",
        shell_runtime="swift",
    )
    text = out.read_text(encoding="utf-8")
    assert "buildiooBridge" in text
    assert "`agent.design`" in text
    assert "`agent.plan.spec`" in text
    assert "`agent.h5`" in text
