"""Tests for path-only agent spec index."""

from __future__ import annotations

from pathlib import Path

from batch.agent_spec_index import (
    SPEC_INDEX_REL,
    prepare_agent_prompt_files,
    write_plan_gate_repair_brief,
)


def test_prepare_agent_prompt_files_writes_index(tmp_path: Path) -> None:
    (tmp_path / "skill-input").mkdir()
    (tmp_path / "skill-input" / "context.json").write_text("{}", encoding="utf-8")
    index, brain = prepare_agent_prompt_files(
        tmp_path,
        phase="plan",
        app_name="Demo",
        pack_type="h5_shell",
        role_slug="build-agent-plan",
        role_focus="- example/path.md",
    )
    assert index.is_file()
    assert brain.is_file()
    body = index.read_text(encoding="utf-8")
    assert "Agent spec index" in body
    assert "Phase: **plan**" in body
    assert (tmp_path / SPEC_INDEX_REL).is_file()


def test_repair_brief_paths_only(tmp_path: Path) -> None:
    write_plan_gate_repair_brief(
        tmp_path,
        issue="missing section",
        focus="add BR rules",
        target_files=("功能文档.md",),
    )
    text = (tmp_path / "skill-input" / "plan-gate-repair-brief.md").read_text(
        encoding="utf-8"
    )
    assert "功能文档.md" in text
    assert "```" not in text
