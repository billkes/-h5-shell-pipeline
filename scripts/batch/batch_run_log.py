"""Queue-style console output + file-only detail lines (WanFaGuiYi-inspired)."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from batch.batch_log import format_log_timestamp, log_detail

if TYPE_CHECKING:
    pass

_run_log: ContextVar[BatchRunLog | None] = ContextVar("batch_run_log", default=None)


@dataclass
class TaskRunContext:
    index: int
    total: int
    name: str
    pack_type: str
    workspace: Path
    desc: str = ""
    detail_lines: list[str] = field(default_factory=list)


class BatchRunLog:
    """Stdout queue lines with ``[HH:MM:SS] [i/n] App | …``; details → file only."""

    def __init__(self) -> None:
        self.task: TaskRunContext | None = None

    @property
    def prefix(self) -> str:
        t = self.task
        if t is None:
            return ""
        return f"[{t.index}/{t.total}] {t.name}"

    def _now(self) -> str:
        return format_log_timestamp()[11:19]

    def queue(self, msg: str) -> None:
        p = self.prefix
        if p:
            print(f"[{self._now()}] {p} | {msg}")
        else:
            print(f"[{self._now()}] {msg}")

    def detail(self, msg: str) -> None:
        if self.task is not None:
            self.task.detail_lines.append(msg)
        p = self.prefix
        line = f"{p} | {msg}" if p else msg
        log_detail(line)

    def banner(self, title: str) -> None:
        print("")
        print("═" * 56)
        print(f"  {title}")
        print("═" * 56)

    def fail_banner(self, title: str, items: list[str], *, max_show: int = 6) -> None:
        print("")
        print("!" * 56)
        print(f"  ❌ {title}")
        for item in items[:max_show]:
            print(f"     · {item}")
        if len(items) > max_show:
            print(f"     · … 共 {len(items)} 项，详见详细日志")
        print("!" * 56)
        print("")
        for item in items:
            self.detail(item)

    def phase_line(
        self,
        phase_num: int,
        label: str,
        status: str,
        elapsed_s: float,
        *,
        note: str = "",
    ) -> None:
        icons = {
            "done": "✅",
            "failed": "❌",
            "skipped": "⏭️",
            "running": "⟳",
        }
        icon = icons.get(status, "❓")
        short = label.split("·", 1)[-1].strip() if "·" in label else label
        msg = f"Phase {phase_num} {short} {icon} ({elapsed_s:.0f}s)"
        if note:
            msg += f" — {note}"
        if status == "skipped":
            self.detail(msg)
            return
        if status == "done" and phase_num <= 2:
            self.detail(f"断点跳过 · {msg}")
            return
        self.queue(msg)

    def flush_task_details(self) -> None:
        t = self.task
        if t is None:
            return
        log_detail(f"========== 任务: {t.name} ==========")
        log_detail(f"类型: {t.pack_type} · 目录: {t.workspace}")
        if t.desc:
            log_detail(f"描述: {t.desc}")
        for line in t.detail_lines:
            log_detail(line)
        log_detail("-" * 40)


def get_run_log() -> BatchRunLog:
    log = _run_log.get()
    if log is None:
        return _NULL_RUN_LOG
    return log


def set_run_log(log: BatchRunLog | None) -> None:
    _run_log.set(log)


class _NullRunLog(BatchRunLog):
    def queue(self, msg: str) -> None:
        print(msg)

    def detail(self, msg: str) -> None:
        pass

    def fail_banner(self, title: str, items: list[str], *, max_show: int = 6) -> None:
        BatchRunLog.fail_banner(self, title, items, max_show=max_show)

    def phase_line(self, *args, **kwargs) -> None:
        pass

    def flush_task_details(self) -> None:
        pass


_NULL_RUN_LOG = _NullRunLog()


def task_failure_headline(workspace: Path) -> str:
    """One-line failure reason for batch summary."""
    from batch.state import (
        PHASE_LABELS,
        PM_PHASE,
        PM_UI_PLAN_PHASE,
        PROGRAMMER_PHASE,
        TEST_PHASE,
        phase_status_from_data,
        phases_for_workspace,
        read_state,
    )

    state = read_state(workspace)
    name = state.get("name") or workspace.name
    phases = phases_for_workspace(workspace)

    if phase_status_from_data(state, PROGRAMMER_PHASE) == "failed":
        reason = (
            state.get("phase_programmer_failure_reason")
            or state.get("phase6_failure_reason")
            or "Programmer gate 失败"
        )
        details = state.get("phase_programmer_failure_details") or state.get(
            "phase6_failure_details"
        ) or []
        extra = ""
        if isinstance(details, list) and details:
            first = str(details[0])
            if "]" in first:
                first = first.split("]", 1)[-1].strip()
            extra = f"（{first[:80]}）"
        return f"{name} — Programmer 未通过: {reason}{extra}"
    if phase_status_from_data(state, TEST_PHASE) == "failed":
        reason = state.get("phase_tester_failure_reason") or state.get(
            "phase7_failure_reason"
        ) or "测试未通过"
        return f"{name} — Tester 未通过: {reason}"
    for phase in reversed(phases):
        if phase_status_from_data(state, phase) == "failed":
            label = PHASE_LABELS.get(phase, phase)
            reason = state.get(f"{phase}_failure_reason") or f"{label} 失败"
            return f"{name} — {label}: {reason}"
    if state.get("phase4") == "done" and state.get("phase6") != "done":
        return f"{name} — 实现完成，analyze 未通过"
    if phase_status_from_data(state, PM_UI_PLAN_PHASE) == "done" and phase_status_from_data(
        state, PROGRAMMER_PHASE
    ) != "done":
        return f"{name} — Plan 完成，Programmer 未完成"
    if phase_status_from_data(state, PM_PHASE) == "done" and phase_status_from_data(
        state, PROGRAMMER_PHASE
    ) != "done":
        return f"{name} — PM 完成，Programmer 未完成"
    return f"{name} — 未完成"


def compact_resume_summary(workspace: Path) -> str:
    from batch.pipeline_steps import steps_for_run
    from batch.state import (
        PHASE_SHORT,
        PIPELINE_V3,
        get_phase,
        phases_for_workspace,
        pipeline_version_from_data,
        read_state,
        steps_map_from_data,
    )

    data = read_state(workspace)
    ver = pipeline_version_from_data(data)
    if ver == PIPELINE_V3:
        steps_map = steps_map_from_data(data)
        pack_type = str(data.get("pack_type") or "contentpack")
        ordered = steps_for_run(pack_type=pack_type)
        icons = {"done": "✅", "failed": "❌", "skipped": "⏭️", "running": "⚡"}
        from batch.pipeline_steps import PHASE_STEPS
        from batch.state import PM_UI_PLAN_PHASE, PROGRAMMER_PHASE

        parts: list[str] = []
        for phase in (PM_UI_PLAN_PHASE, PROGRAMMER_PHASE):
            phase_steps = [s for s in PHASE_STEPS.get(phase, ()) if s in ordered]
            if not phase_steps:
                continue
            statuses = [steps_map.get(s, "pending") for s in phase_steps]
            if all(s == "pending" for s in statuses):
                continue
            status = (
                "failed"
                if any(s == "failed" for s in statuses)
                else "running"
                if any(s == "running" for s in statuses)
                else "skipped"
                if all(s == "skipped" for s in statuses)
                else "done"
                if all(s == "done" for s in statuses)
                else "running"
            )
            label = PHASE_SHORT.get(phase, phase)
            icon = icons.get(status, "?")
            suffix = " 将重试" if status in ("failed", "running") else ""
            parts.append(f"{label}{icon}{suffix}")
        if not parts:
            return "断点: 全新任务"
        done = sum(1 for s in ordered if steps_map.get(s) == "done")
        return f"断点续跑 ({done}/{len(ordered)}): " + " · ".join(parts)

    phases = phases_for_workspace(workspace)
    groups: list[str] = []
    i = 0
    while i < len(phases):
        status = get_phase(workspace, phases[i])
        if status == "pending":
            i += 1
            continue
        j = i
        while j + 1 < len(phases) and get_phase(workspace, phases[j + 1]) == status:
            j += 1
        label_a = PHASE_SHORT.get(phases[i], phases[i])
        label_b = PHASE_SHORT.get(phases[j], phases[j])
        label = label_a if label_a == label_b else f"{label_a}-{label_b}"
        icon = {"done": "✅", "failed": "❌", "skipped": "⏭️", "running": "⚡"}.get(
            status, "?"
        )
        suffix = " 将重试" if status in ("failed", "running") else ""
        groups.append(f"{label}{icon}{suffix}")
        i = j + 1
    if not groups:
        return "断点: 全新任务"
    return "断点续跑: " + " · ".join(groups)
