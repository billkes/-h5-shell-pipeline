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
    PLAN_GATE,
    PREVIEW_TABS,
    SKILL_ENRICH,
    SKILL_PAGES,
    SKILL_TOKENS,
    steps_for_run,
)
from batch.pipeline_v3_runner import V3StepRunner  # noqa: E402
from batch.state import (  # noqa: E402
    get_step,
    read_state,
    set_step,
    steps_map_from_data,
    sync_phases_from_steps,
    update_state_fields,
)


def test_build_agent_done_backfills_pending_skill_steps() -> None:
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
    assert migrated[SKILL_ENRICH] == "done"
    assert migrated[SKILL_PAGES] == "done"
    assert migrated[SKILL_TOKENS] == "done"


def test_build_agent_done_backfills_preview_tabs() -> None:
    raw = {
        "pack_type": "h5_oc_shell",
        "steps": {
            "prepare.context": "done",
            "skill.design": "done",
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
                    "skill.enrich": "pending",
                    "skill.pages": "pending",
                    "skill.tokens": "pending",
                    BUILD_AGENT: "running",
                },
            }
        ),
        encoding="utf-8",
    )
    set_step(ws, BUILD_AGENT, "done")
    data = read_state(ws)
    assert data["steps"][SKILL_ENRICH] == "done"
    assert data["steps"][SKILL_PAGES] == "done"
    assert data["steps"][SKILL_TOKENS] == "done"
    assert data["steps"][PREVIEW_TABS] == "done"


def test_prerequisites_ok_after_build_agent_done() -> None:
    td = Path(tempfile.mkdtemp())
    ws = td / "App"
    ws.mkdir()
    (ws / ".build-state.json").write_text(
        json.dumps(
            {
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
                },
            }
        ),
        encoding="utf-8",
    )

    class _Pipeline:
        cfg = None

    runner = V3StepRunner(_Pipeline())

    class _Ctx:
        pack_type = "h5_oc_shell"
        workspace = ws

    assert get_step(ws, SKILL_ENRICH) == "done"
    assert runner._prerequisites_ok(_Ctx(), PLAN_GATE) is True
