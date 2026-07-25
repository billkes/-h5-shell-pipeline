"""Pre-fill the four main Agent prompts after lock.dimensions.

Writes exactly four filled prompt files under ``skill-input/agent-prompts/``
plus a runbook (outside that folder) that marks execution order.
Runtime Agent steps still re-fill prompts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from batch.agent_spec_index import prepare_agent_prompt_files
from batch.pipeline_steps import (
    AGENT_H5,
    AGENT_PLAN_PACK,
    AGENT_PLAN_SPEC,
    AGENT_SHELL,
    STEP_LABELS,
)
from batch.prompts import (
    PromptBuilder,
    _PM_UI_PLAN_BRAIN_FOCUS,
    _PROGRAMMER_BRAIN_FOCUS,
)

AGENT_PROMPTS_DIR = "skill-input/agent-prompts"
RUNBOOK_MD_REL = "skill-input/agent-runbook.md"
RUNBOOK_JSON_REL = "skill-input/agent-runbook.json"


@dataclass(frozen=True)
class AgentPromptSlot:
    seq: int
    step_id: str
    phase: str
    role_slug: str
    role_focus: str
    builder_name: str
    prerequisites: tuple[str, ...]
    deliverables: tuple[str, ...]


MAIN_AGENT_SLOTS: tuple[AgentPromptSlot, ...] = (
    AgentPromptSlot(
        seq=1,
        step_id=AGENT_PLAN_SPEC,
        phase="plan_spec",
        role_slug="build-agent-plan-spec",
        role_focus=_PM_UI_PLAN_BRAIN_FOCUS,
        builder_name="build_agent_plan_spec_phase",
        prerequisites=("lock.dimensions done", "sync.distilled done"),
        deliverables=(
            "功能文档.md",
            "{name} Privacy Agreement.md",
            "{name} User Agreement.md",
        ),
    ),
    AgentPromptSlot(
        seq=2,
        step_id=AGENT_PLAN_PACK,
        phase="plan_pack",
        role_slug="build-agent-plan-pack",
        role_focus=_PM_UI_PLAN_BRAIN_FOCUS,
        builder_name="build_agent_plan_pack_phase",
        prerequisites=(f"{AGENT_PLAN_SPEC} done", "功能文档.md"),
        deliverables=("本包登记信息.json", "本包视觉锁.json"),
    ),
    AgentPromptSlot(
        seq=3,
        step_id=AGENT_SHELL,
        phase="shell",
        role_slug="build-agent-shell",
        role_focus=_PROGRAMMER_BRAIN_FOCUS,
        builder_name="build_agent_shell_phase",
        prerequisites=(
            f"{AGENT_PLAN_PACK} done",
            "本包登记信息.json",
            "本包视觉锁.json",
        ),
        deliverables=("native / Flutter shell + Bridge",),
    ),
    AgentPromptSlot(
        seq=4,
        step_id=AGENT_H5,
        phase="h5",
        role_slug="build-agent-h5",
        role_focus=_PROGRAMMER_BRAIN_FOCUS,
        builder_name="build_agent_h5_phase",
        prerequisites=(f"{AGENT_SHELL} done",),
        deliverables=("h5/ vault · legal overlay · plaza",),
    ),
)


def _prompt_filename(slot: AgentPromptSlot) -> str:
    return f"{slot.seq:02d}-{slot.step_id}.md"


def _header(*, seq: int, step_id: str, app_name: str, pack_type: str) -> str:
    return (
        f"<!-- agent-run: seq={seq} step={step_id} "
        f"app={app_name} pack={pack_type} -->\n"
    )


def _clear_agent_prompts_dir(out_dir: Path) -> None:
    """Keep agent-prompts/ containing only the four filled prompts."""
    if not out_dir.is_dir():
        return
    for path in out_dir.iterdir():
        if path.is_file():
            path.unlink()


def write_agent_prompt_pack(
    workspace: Path,
    *,
    prompts: PromptBuilder,
    pack_context: dict[str, Any],
    app_name: str,
    pack_type: str,
    resume: bool = False,
) -> dict[str, Any]:
    """Fill and write the four main Agent prompts + runbook. Returns runbook dict."""
    workspace = workspace.expanduser().resolve()
    out_dir = workspace / AGENT_PROMPTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    _clear_agent_prompts_dir(out_dir)

    name = str(pack_context.get("name") or app_name)
    entries: list[dict[str, Any]] = []

    for slot in MAIN_AGENT_SLOTS:
        build: Callable[..., str] = getattr(prompts, slot.builder_name)
        body = build(resume=resume, **pack_context)
        prompt_rel = f"{AGENT_PROMPTS_DIR}/{_prompt_filename(slot)}"
        prompt_text = (
            _header(
                seq=slot.seq,
                step_id=slot.step_id,
                app_name=app_name,
                pack_type=pack_type,
            )
            + body
        )
        (workspace / prompt_rel).write_text(prompt_text, encoding="utf-8")

        deliverables = tuple(
            d.replace("{name}", name) for d in slot.deliverables
        )
        entries.append(
            {
                "seq": slot.seq,
                "step_id": slot.step_id,
                "label": STEP_LABELS.get(slot.step_id, slot.step_id),
                "phase": slot.phase,
                "prompt": prompt_rel.replace("\\", "/"),
                "prerequisites": list(slot.prerequisites),
                "deliverables": list(deliverables),
            }
        )

    # Leave live index/brain ready for the first Agent step.
    first = MAIN_AGENT_SLOTS[0]
    prepare_agent_prompt_files(
        workspace,
        phase=first.phase,  # type: ignore[arg-type]
        app_name=app_name,
        pack_type=pack_type,
        role_slug=first.role_slug,
        role_focus=first.role_focus,
    )

    stamped = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    runbook: dict[str, Any] = {
        "app": app_name,
        "pack_type": pack_type,
        "generated_at": stamped,
        "note": (
            "Review snapshots filled after lock.dimensions. "
            "Runtime Agent steps re-fill prompts before each call."
        ),
        "execution_order": entries,
    }

    (workspace / RUNBOOK_JSON_REL).write_text(
        json.dumps(runbook, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (workspace / RUNBOOK_MD_REL).write_text(
        _format_runbook_md(runbook),
        encoding="utf-8",
    )
    return runbook


def _format_runbook_md(runbook: dict[str, Any]) -> str:
    lines = [
        "# Agent runbook",
        "",
        f"- App: **{runbook['app']}**",
        f"- Pack: `{runbook['pack_type']}`",
        f"- Generated: `{runbook['generated_at']}`",
        "",
        runbook.get("note") or "",
        "",
        "| # | step | prompt | prerequisites | deliverables |",
        "|---|------|--------|---------------|--------------|",
    ]
    for entry in runbook.get("execution_order") or []:
        seq = entry["seq"]
        step = entry["step_id"]
        prompt = entry["prompt"]
        prereq = "; ".join(entry.get("prerequisites") or [])
        outs = "; ".join(entry.get("deliverables") or [])
        lines.append(
            f"| {seq} | `{step}` | `{prompt}` | {prereq} | {outs} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- `{RUNBOOK_JSON_REL}` — machine-readable order",
            f"- `{AGENT_PROMPTS_DIR}/0N-<step>.md` — filled prompts (exactly 4)",
            "",
        ]
    )
    return "\n".join(lines)
