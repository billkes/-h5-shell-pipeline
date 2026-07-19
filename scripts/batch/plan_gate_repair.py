"""plan.gate soft/hard issue prioritization and targeted Agent repair."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepairTarget:
    issue: str
    priority: int
    target_files: tuple[str, ...]
    focus: str
    category: str  # hard | soft


_HARD_FILE_MAP: tuple[tuple[str, str, str], ...] = (
    ("缺少 功能文档", "功能文档.md", "补写功能文档.md 全部强制章节"),
    ("缺少 本包登记", "本包登记信息.json", "补写本包登记信息.json H5 必填字段"),
    ("缺少 视觉蓝图", "视觉蓝图.md", "补写视觉蓝图.md V2 章节"),
    ("缺少 本包视觉锁", "本包视觉锁.json", "补写本包视觉锁.json V2 字段"),
    ("缺少 design-system MASTER", "design-system", "补写 design-system/*/MASTER.md"),
)


def plan_gate_repair_max_rounds() -> int:
    raw = os.environ.get("PLAN_GATE_REPAIR_MAX_ROUNDS", "2").strip()
    try:
        return max(0, min(5, int(raw)))
    except ValueError:
        return 2


def plan_gate_repair_enabled() -> bool:
    return os.environ.get("ENABLE_PLAN_GATE_REPAIR", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _priority_for_issue(issue: str) -> tuple[int, str, str]:
    """Return (priority, focus, category) — lower priority number = fix first."""
    if issue.startswith("[FLOW-"):
        return 10, "重写 Primary Workflow 以匹配 interactionTopology，去除 CRUD 套话", "soft"
    if issue.startswith("[SPEC-002]") or "缺少" in issue and "章节" in issue:
        return 20, "补全功能文档.md 缺失核心章节（Domain Model / Primary Workflow 等）", "soft"
    if issue.startswith("[SPEC-003]") or issue.startswith("[SPEC-004]"):
        return 30, "加深功能文档 Business Rules 与 Primary Workflow 步骤", "soft"
    if issue.startswith("[SEL-"):
        return 40, "对齐视觉蓝图 §Component Selection 与视觉锁 componentSelection", "soft"
    if issue.startswith("视觉蓝图"):
        return 50, "补全视觉蓝图.md 对应 V2 章节深度", "soft"
    if "Data Contract" in issue or "数据契约" in issue:
        return 60, "在功能文档.md 增加 Data Contract / 数据契约 章节", "soft"

    if issue.startswith("[SPEC-"):
        return 35, "按 SPEC 缺口补写功能文档.md 业务深度", "soft"
    return 80, "按拒因最小改动修复对应 deliverable", "soft"


def pick_hard_repair_target(hard: list[str]) -> RepairTarget | None:
    for issue in hard:
        for prefix, file_hint, focus in _HARD_FILE_MAP:
            if prefix in issue:
                return RepairTarget(
                    issue=issue,
                    priority=1,
                    target_files=(file_hint,),
                    focus=focus,
                    category="hard",
                )
        if "JSON 不合法" in issue or "缺少字段" in issue:
            fname = "本包登记信息.json"
            if "视觉锁" in issue:
                fname = "本包视觉锁.json"
            return RepairTarget(
                issue=issue,
                priority=2,
                target_files=(fname,),
                focus=f"修复 {fname} 结构与必填字段",
                category="hard",
            )
    return None


def pick_soft_repair_target(soft: list[str]) -> RepairTarget | None:
    if not soft:
        return None
    ranked: list[tuple[int, str, str, str]] = []
    for issue in soft:
        prio, focus, cat = _priority_for_issue(issue)
        ranked.append((prio, issue, focus, cat))
    ranked.sort(key=lambda x: x[0])
    _, issue, focus, cat = ranked[0]
    files = ("功能文档.md",)
    if issue.startswith("[SEL-") or "视觉蓝图" in issue or "Component Selection" in issue:
        files = ("视觉蓝图.md", "本包视觉锁.json")
    return RepairTarget(
        issue=issue,
        priority=ranked[0][0],
        target_files=files,
        focus=focus,
        category=cat,
    )


def pick_repair_target(*, hard: list[str], soft: list[str]) -> RepairTarget | None:
    """Pick single highest-priority repair target."""
    hard_target = pick_hard_repair_target(hard)
    if hard_target:
        return hard_target
    return pick_soft_repair_target(soft)


def build_repair_prompt(
    workspace: Path,
    target: RepairTarget,
    *,
    app_name: str,
    desc: str,
    project_dir: Path | None = None,
    **_: object,
) -> str:
    """Build a minimal Agent prompt for one targeted plan.gate fix."""
    from batch.agent_spec_index import (
        write_agent_spec_index,
        write_plan_gate_repair_brief,
    )
    from batch.config import BatchConfig
    from batch.prompts import PromptBuilder

    cfg = BatchConfig.from_env()
    if project_dir is not None:
        cfg.project_dir = project_dir
    store = PromptBuilder(cfg)

    constraints = ""
    ctx_path = workspace / "skill-input" / "context.json"
    if ctx_path.is_file():
        try:
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
            tier = ((ctx.get("constraints") or {}).get("businessDepthTier") or "L2")
            topo = ((ctx.get("constraints") or {}).get("interactionTopology") or "")
            constraints = f"businessDepthTier={tier}; interactionTopology={topo}"
        except json.JSONDecodeError:
            pass

    write_plan_gate_repair_brief(
        workspace,
        issue=target.issue,
        focus=target.focus,
        target_files=target.target_files,
        constraints=constraints,
    )
    write_agent_spec_index(
        workspace,
        phase="repair",
        app_name=app_name,
        pack_type="h5_shell",
    )

    return store._fmt(
        store._load("phase_plan_gate_repair.txt"),
        {"name": app_name, "desc": desc},
    )


def append_repair_history(workspace: Path, *, round_no: int, target: RepairTarget, ok: bool) -> None:
    report_path = workspace / "plan-gate-report.json"
    payload: dict = {}
    if report_path.is_file():
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    history = list(payload.get("repairHistory") or [])
    history.append(
        {
            "round": round_no,
            "issue": target.issue,
            "focus": target.focus,
            "files": list(target.target_files),
            "category": target.category,
            "agentOk": ok,
        }
    )
    payload["repairHistory"] = history
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
