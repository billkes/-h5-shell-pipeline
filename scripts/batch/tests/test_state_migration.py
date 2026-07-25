"""Tests for .build-state.json step migration and build.agent backfill."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

from batch.pipeline_steps import (  # noqa: E402
    BUILD_AGENT,
    PREVIEW_TABS,
    SKILL_ENRICH,
    SKILL_PAGES,
    SKILL_TOKENS,
)
from batch.state import (  # noqa: E402
    read_state,
    set_step,
    steps_map_from_data,
)


def test_retired_skill_steps_are_dropped_from_state() -> None:
    raw = {
        "pack_type": "h5_oc_shell",
        "steps": {
            "prepare.context": "done",
            "skill.design": "done",
            "skill.enrich": "pending",
            "skill.adapt": "done",
            "skill.pages": "pending",
            "skill.tokens": "pending",
            "lock.dimensions": "done",
            BUILD_AGENT: "done",
            "plan.gate": "skipped",
        },
    }
    migrated = steps_map_from_data(raw)
    assert SKILL_ENRICH not in migrated
    assert SKILL_PAGES not in migrated
    assert SKILL_TOKENS not in migrated
    assert "skill.design" not in migrated
    assert migrated["prepare.context"] == "done"
    assert migrated["lock.dimensions"] == "done"


def test_build_agent_done_backfills_preview_tabs() -> None:
    raw = {
        "pack_type": "h5_oc_shell",
        "steps": {
            "prepare.context": "done",
            "lock.dimensions": "done",
            "preview.tabs": "pending",
            BUILD_AGENT: "done",
        },
    }
    migrated = steps_map_from_data(raw)
    assert migrated[PREVIEW_TABS] == "done"


def test_set_step_build_agent_backfills_prep_chain() -> None:
    td = Path(tempfile.mkdtemp())
    ws = td / "App"
    ws.mkdir()
    (ws / ".build-state.json").write_text(
        json.dumps(
            {
                "pack_type": "h5_oc_shell",
                "steps": {
                    BUILD_AGENT: "running",
                },
            }
        ),
        encoding="utf-8",
    )
    set_step(ws, BUILD_AGENT, "done")
    data = read_state(ws)
    assert data["steps"]["prepare.context"] == "done"
    assert data["steps"]["lock.dimensions"] == "done"
    assert data["steps"][PREVIEW_TABS] == "done"
    assert SKILL_ENRICH not in data["steps"]


def test_build_agent_done_expands_to_granular_agents() -> None:
    raw = {
        "pack_type": "h5_oc_shell",
        "steps": {
            "prepare.context": "done",
            "lock.dimensions": "done",
            BUILD_AGENT: "done",
        },
    }
    migrated = steps_map_from_data(raw)
    assert migrated.get("agent.design") == "done"
    assert migrated.get("agent.plan.spec") == "done"
    assert migrated.get("agent.shell") == "done"
    assert migrated.get("agent.h5") == "done"
