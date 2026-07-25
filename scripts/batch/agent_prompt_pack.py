"""Pre-fill the main Agent prompts after lock.dimensions.

Writes filled prompt files under ``skill-input/agent-prompts/``
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
    AGENT_DESIGN,
    AGENT_H5,
    AGENT_PLAN_PACK,
    AGENT_PLAN_SPEC,
    AGENT_SHELL,
    STEP_LABELS,
)
from batch.prompts import (
    PromptBuilder,
    _DESIGN_AGENT_BRAIN_FOCUS,
    _PM_UI_PLAN_BRAIN_FOCUS,
    _PROGRAMMER_BRAIN_FOCUS,
)

AGENT_PROMPTS_DIR = "skill-input/agent-prompts"
RUNBOOK_MD_REL = "skill-input/agent-runbook.md"
RUNBOOK_JSON_REL = "skill-input/agent-runbook.json"
WEB_AGENT_RESUME_MD_REL = "网页Agent续跑手册.md"


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
        step_id=AGENT_DESIGN,
        phase="design",
        role_slug="build-agent-design",
        role_focus=_DESIGN_AGENT_BRAIN_FOCUS,
        builder_name="build_agent_design_phase",
        prerequisites=("lock.dimensions done", "sync.distilled done"),
        deliverables=(
            "design-system/*/MASTER.md (audited/repaired)",
            "skill-adapt/design-audit.md",
        ),
    ),
    AgentPromptSlot(
        seq=2,
        step_id=AGENT_PLAN_SPEC,
        phase="plan_spec",
        role_slug="build-agent-plan-spec",
        role_focus=_PM_UI_PLAN_BRAIN_FOCUS,
        builder_name="build_agent_plan_spec_phase",
        prerequisites=(f"{AGENT_DESIGN} done", "skill-adapt/design-audit.md"),
        deliverables=(
            "功能文档.md",
            "{name} Privacy Agreement.md",
            "{name} User Agreement.md",
        ),
    ),
    AgentPromptSlot(
        seq=3,
        step_id=AGENT_PLAN_PACK,
        phase="plan_pack",
        role_slug="build-agent-plan-pack",
        role_focus=_PM_UI_PLAN_BRAIN_FOCUS,
        builder_name="build_agent_plan_pack_phase",
        prerequisites=(f"{AGENT_PLAN_SPEC} done", "功能文档.md"),
        deliverables=("本包登记信息.json", "本包视觉锁.json"),
    ),
    AgentPromptSlot(
        seq=4,
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
        seq=5,
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
    """Keep agent-prompts/ containing only the filled main Agent prompts."""
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
    """Fill and write the main Agent prompts + runbook. Returns runbook dict."""
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
            f"- `{AGENT_PROMPTS_DIR}/0N-<step>.md` — filled prompts "
            f"(exactly {len(MAIN_AGENT_SLOTS)})",
            f"- `{WEB_AGENT_RESUME_MD_REL}` — web Agent resume (written at sync.distilled)",
            "",
        ]
    )
    return "\n".join(lines)


def _bridge_names(app_name: str) -> tuple[str, str]:
    """App-name Bridge channel + callback (never derive from code prefix)."""
    app_lower = "".join(ch for ch in app_name.strip() if ch.isalnum()).lower()
    if not app_lower:
        app_lower = "app"
    return f"{app_lower}Bridge", f"{app_lower}BridgeCallback"


def _load_runbook(workspace: Path) -> dict[str, Any] | None:
    path = workspace / RUNBOOK_JSON_REL
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _format_web_agent_resume_md(
    *,
    app_name: str,
    pack_type: str,
    prefix: str,
    shell_runtime: str,
    generated_at: str,
    execution_order: list[dict[str, Any]],
) -> str:
    bridge, bridge_cb = _bridge_names(app_name)
    prefix_display = prefix or "(见 本包代码组合.json / dartCodePrefix)"
    runtime_display = shell_runtime or "native"

    step_rows: list[str] = []
    for entry in execution_order:
        seq = entry.get("seq", "?")
        step = entry.get("step_id", "")
        prompt = entry.get("prompt", "")
        outs = "; ".join(entry.get("deliverables") or []) or "—"
        step_rows.append(
            f"| {seq} | `{step}` | `{prompt}` | {outs} |"
        )
    if not step_rows:
        for slot in MAIN_AGENT_SLOTS:
            prompt = f"{AGENT_PROMPTS_DIR}/{_prompt_filename(slot)}"
            outs = "; ".join(
                d.replace("{name}", app_name) for d in slot.deliverables
            )
            step_rows.append(
                f"| {slot.seq} | `{slot.step_id}` | `{prompt}` | {outs} |"
            )

    lines = [
        f"# 网页 Agent 续跑手册 — {app_name}",
        "",
        "> 由流水线 `sync.distilled`（第 8 步）写入。供网页版 Agent 手工续跑剩余 Agent 步骤；"
        "**不改变**流水线步骤定义与 `run.sh` 用法。",
        "",
        "## 背景",
        "",
        f"- App: **{app_name}**",
        f"- Pack: `{pack_type}`",
        f"- Runtime: `{runtime_display}`",
        f"- Prefix（代码前缀，≠ Bridge 名）: `{prefix_display}`",
        f"- Generated: `{generated_at}`",
        "- 流水线 1–8 已完成（`prepare.context` → `sync.distilled`）——skill 设计产物为**草稿**",
        f"- 从下方步骤 1 起串行执行 **{len(MAIN_AGENT_SLOTS)} 个 Agent**；"
        "总表见 `skill-input/agent-runbook.md`",
        "",
        "## 工作区",
        "",
        "- 根目录 = 本包根（本文件所在目录）",
        "- 只读/写本根下文件；禁止出包",
        "- Preferred index: `skill-input/agent-spec-index.md` · "
        "`skill-input/agent-workspace-focus.md`",
        "- 技能用法：`H5壳ui-ux-pro-max使用规范.md`（**步骤 1 `agent.design` 主责**）",
        "",
        "## 执行顺序（严格串行）",
        "",
        "| # | step | prompt | deliverables |",
        "|---|------|--------|--------------|",
        *step_rows,
        "",
        "## 每步协议",
        "",
        "1. 完整阅读对应 `skill-input/agent-prompts/0N-*.md`",
        "2. 再读该 prompt 内 Required Reading（规范与 distilled 路径）",
        "3. **只写**该步 Deliverables；不要提前做下一步",
        "4. 自检通过后再进入下一步",
        "5. 一步结束只输出一行 summary",
        "",
        "## 硬约束（摘要）",
        "",
        f"- Bridge 锁定（按 App 名，**禁止**用 prefix 派生）: "
        f"`{bridge}` / `{bridge_cb}`",
        "- Shell 无业务 UI；业务只在 `h5/`",
        "- **`agent.design`**：审核/修复 MASTER（禁消费向 SaaS）；写出 "
        "`skill-adapt/design-audit.md`",
        "- 后续步骤默认信任 design-audit；Pack 只锁视觉，H5 做两阶段实现",
        "- H5 两阶段：先 `_preview/pages` HTML（FREEZE）→ 再移植 `h5/`；gate 只验 `h5/`",
        "- 禁止对照其他包 `output/` / `h5/` / `_preview/` / MASTER 当模板",
        "- 不编辑 `h5_site/`（部署产物由流水线 `dev.h5.build` 生成）",
        "- 若缺少 `产包计划.md`：跳过该文件，以 `功能文档.md` + 登记 JSON 为准",
        "- H5 用户可见文案：English；浏览器 DEV 须接 `browserMock`",
        "",
        "## Agent 全部完成后",
        "",
        f"- **默认**：{len(MAIN_AGENT_SLOTS)} 个 Agent 做完即停，交回原流水线续跑 "
        "`plan.gate` → `dev.h5.build` → `git.plan` / `git.dev`",
        "- 仅当用户明确说「继续到可 build」时：在 `h5/` 内修到可 "
        "`npm run build:deploy`；仍不改流水线代码与步骤",
        "",
        "## 启动话术（粘贴给网页 Agent）",
        "",
        "```text",
        f"请打开并严格遵循 @{WEB_AGENT_RESUME_MD_REL}。",
        f"从「执行顺序」步骤 1 串行做到步骤 {len(MAIN_AGENT_SLOTS)}；每步验收后再继续。",
        "先做 agent.design（设计审核），再 plan/shell/h5。",
        "工作区仅限本包根目录；Bridge 名勿用代码前缀派生。",
        "```",
        "",
    ]
    return "\n".join(lines)


def write_web_agent_resume_handbook(
    workspace: Path,
    *,
    app_name: str,
    pack_type: str,
    prefix: str = "",
    shell_runtime: str = "",
) -> Path:
    """Write package-root handbook for web Agents after sync.distilled.

    Does not change V3 step order. Relies on agent-runbook.json from
    lock.dimensions when present; falls back to MAIN_AGENT_SLOTS.
    """
    workspace = workspace.expanduser().resolve()
    runbook = _load_runbook(workspace)
    stamped = (
        str(runbook.get("generated_at") or "")
        if runbook
        else ""
    ) or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    execution_order = list((runbook or {}).get("execution_order") or [])
    text = _format_web_agent_resume_md(
        app_name=app_name,
        pack_type=pack_type,
        prefix=prefix,
        shell_runtime=shell_runtime,
        generated_at=stamped,
        execution_order=execution_order,
    )
    out = workspace / WEB_AGENT_RESUME_MD_REL
    out.write_text(text, encoding="utf-8")
    return out
