"""Generate batch Markdown reports from .build-state.json files."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from batch.state import (
    ASSETS_PHASE,
    PHASE_LABELS,
    PM_PHASE,
    PM_UI_PLAN_PHASE,
    PROGRAMMER_PHASE,
    TEST_PHASE,
    UI_PHASE,
    final_phase_for_version,
    phase_status_from_data,
    phases_for_version,
    pipeline_version_from_data,
)


def _fmt_dur(seconds: int | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60:02d}s"
    return f"{s // 3600}h {(s % 3600) // 60}m {s % 60:02d}s"


def _phase_icon(status: str | None) -> str:
    return {
        "done": "✅",
        "failed": "❌",
        "pending": "⬜",
        "running": "⚡",
        "skipped": "⏭️",
    }.get(status or "pending", "❓")


def _failure_reason(app: dict, phase: str) -> str:
    for key in (f"{phase}_failure_reason",):
        val = app.get(key)
        if val:
            return str(val)
    if phase == PROGRAMMER_PHASE:
        return str(app.get("phase6_failure_reason") or "")
    if phase == TEST_PHASE:
        return str(app.get("phase7_failure_reason") or "")
    if phase == ASSETS_PHASE:
        return str(app.get("phase_assets_failure_reason") or "")
    return ""


def _failure_details(app: dict, phase: str) -> list:
    details = app.get(f"{phase}_failure_details")
    if isinstance(details, list) and details:
        return details
    if phase == PROGRAMMER_PHASE:
        legacy = app.get("phase6_failure_details")
        return legacy if isinstance(legacy, list) else []
    if phase == TEST_PHASE:
        legacy = app.get("phase7_failure_details")
        return legacy if isinstance(legacy, list) else []
    return []


def _failure_lines(app: dict) -> list[str]:
    lines: list[str] = []
    name = app.get("name") or Path(app["_workspace"]).name

    for phase in phases_for_version(pipeline_version_from_data(app)):
        status = phase_status_from_data(app, phase)
        if status != "failed":
            continue
        label = PHASE_LABELS.get(phase, phase)
        reason = _failure_reason(app, phase) or f"{label} 失败"
        lines.append(f"### {name} · {label}")
        lines.append("")
        lines.append(f"- **原因**: {reason}")
        details = _failure_details(app, phase)
        if details:
            lines.append("- **明细**:")
            for item in details:
                lines.append(f"  - {item}")
        if phase == PROGRAMMER_PHASE:
            log_ref = app.get("phase_programmer_analyze_log") or app.get("phase6_analyze_log")
            if log_ref:
                lines.append(f"- **analyze 日志**: `{log_ref}`")
        if phase == TEST_PHASE:
            log_ref = app.get("phase_tester_test_log") or app.get("phase7_test_log")
            if log_ref:
                lines.append(f"- **flutter test 日志**: `{log_ref}`")
            report_ref = app.get("phase_tester_report") or app.get("phase7_tester_report")
            if report_ref:
                lines.append(f"- **测试员报告**: `{report_ref}`")
        lines.append("")

    return lines


def generate_batch_report(
    output_base: Path,
    batch_started_at: str,
    report_file: Path,
    *,
    detailed_log_file: Path | None = None,
    batch_elapsed_s: int | None = None,
    failed_tasks: list[str] | None = None,
) -> Path | None:
    apps: list[dict] = []
    for sf in sorted(output_base.rglob(".build-state.json")):
        if not sf.is_file():
            continue
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            data["_workspace"] = str(sf.parent)
            apps.append(data)
        except json.JSONDecodeError:
            continue
    if not apps:
        return None

    done_full: list[dict] = []
    done_programmer_only: list[dict] = []
    partial_plan: list[dict] = []
    not_started: list[dict] = []

    for a in apps:
        ver = pipeline_version_from_data(a)
        final = final_phase_for_version(ver)
        if phase_status_from_data(a, final) == "done":
            done_full.append(a)
            continue
        if phase_status_from_data(a, PROGRAMMER_PHASE) == "done":
            done_programmer_only.append(a)
            continue
        plan_phase = PM_UI_PLAN_PHASE if ver != "v2" else PM_PHASE
        if phase_status_from_data(a, plan_phase) == "done":
            partial_plan.append(a)
            continue
        not_started.append(a)

    lines = [
        "# Flutter 批量生产执行报告",
        "",
        f"- 生成时间: {datetime.now().isoformat(timespec='seconds')}",
        f"- 批次开始: {batch_started_at}",
        f"- 输出目录: `{output_base}`",
        f"- App 总数: **{len(apps)}**",
    ]
    if batch_elapsed_s is not None:
        lines.append(f"- 总耗时: {_fmt_dur(batch_elapsed_s)}")
    if detailed_log_file is not None:
        lines.append(f"- 详细日志: `{detailed_log_file}`")
    lines.extend(
        [
            "",
            "## 一眼概览",
            "",
        ]
    )
    overview: list[str] = []
    for app in apps:
        name = app.get("name") or Path(app["_workspace"]).name
        ver = pipeline_version_from_data(app)
        final = final_phase_for_version(ver)
        if phase_status_from_data(app, final) == "done":
            overview.append(f"- ✅ **{name}** — 全流程完成")
            continue
        if phase_status_from_data(app, PROGRAMMER_PHASE) == "failed":
            reason = _failure_reason(app, PROGRAMMER_PHASE) or "Programmer gate 失败"
            overview.append(f"- ❌ **{name}** — {reason}")
            continue
        if ver == "v2" and phase_status_from_data(app, TEST_PHASE) == "failed":
            reason = _failure_reason(app, TEST_PHASE) or "测试未通过"
            overview.append(f"- ❌ **{name}** — {reason}")
            continue
        if ver != "v2" and phase_status_from_data(app, PM_UI_PLAN_PHASE) == "failed":
            reason = _failure_reason(app, PM_UI_PLAN_PHASE) or "Plan gate 失败"
            overview.append(f"- ❌ **{name}** — {reason}")
            continue
        plan_phase = PM_UI_PLAN_PHASE if ver != "v2" else PM_PHASE
        if phase_status_from_data(app, plan_phase) == "done":
            overview.append(f"- 🟡 **{name}** — 蓝图完成，Programmer 未完成")
            continue
        overview.append(f"- ❌ **{name}** — 未开始")
    if overview:
        lines.extend(overview)
    else:
        lines.append("- （无 app 状态）")
    lines.extend(
        [
            "",
            "## 汇总",
            "",
            "| 状态 | 数量 |",
            "|------|------|",
            f"| ✅ 全流程完成 | {len(done_full)} |",
            f"| ⚠️ Programmer 完成，后续未完成 | {len(done_programmer_only)} |",
            f"| 🟡 蓝图完成，Programmer 未完成 | {len(partial_plan)} |",
            f"| ❌ 未开始 | {len(not_started)} |",
            "",
        ]
    )

    failure_blocks: list[str] = []
    for app in apps:
        failure_blocks.extend(_failure_lines(app))
    if failure_blocks:
        lines.append("## 失败详情")
        lines.append("")
        lines.extend(failure_blocks)

    if failed_tasks:
        lines.append("## 失败或未支持的任务")
        lines.append("")
        for item in failed_tasks:
            lines.append(f"- `{item}`")
        lines.append("")

    lines.append("## 各 App 步骤明细")
    lines.append("")
    for app in apps:
        name = app.get("name") or Path(app["_workspace"]).name
        lines.append(f"### {name}")
        lines.append("")
        ver = pipeline_version_from_data(app)
        if ver == "v3":
            from batch.pipeline_steps import ANALYZE, step_display, step_duration_key, steps_for_run

            pack_type = str(app.get("pack_type") or "contentpack")
            ordered = steps_for_run(pack_type=pack_type)
            steps_map = app.get("steps") if isinstance(app.get("steps"), dict) else {}
            for step_id in ordered:
                status = str(steps_map.get(step_id) or "pending")
                dur = app.get(step_duration_key(step_id))
                extra = ""
                if step_id == ANALYZE and status == "failed":
                    reason = app.get("phase_programmer_failure_reason")
                    if reason:
                        extra = f" · {reason}"
                lines.append(
                    f"- {_phase_icon(status)} **{step_display(step_id)}** "
                    f"({status}{extra}, {_fmt_dur(dur)})"
                )
            lines.append("")
            continue
        for phase in phases_for_version(ver):
            status = phase_status_from_data(app, phase)
            dur = app.get(f"{phase}_duration_s")
            label = PHASE_LABELS.get(phase, phase)
            extra = ""
            if phase == PROGRAMMER_PHASE:
                total = app.get("phase_programmer_image_total") or app.get("phase6_image_total")
                ph = app.get(
                    "phase_programmer_image_placeholder",
                    app.get("phase6_image_placeholder", 0),
                )
                if total:
                    extra = f" · {total} 张（占位 {ph}）"
                if status == "failed":
                    reason = _failure_reason(app, phase)
                    if reason:
                        extra += f" · {reason}"
            if phase == TEST_PHASE and status == "failed":
                reason = _failure_reason(app, phase)
                if reason:
                    extra += f" · {reason}"
            lines.append(
                f"- {_phase_icon(status)} **{label}** "
                f"({status}{extra}, {_fmt_dur(dur)})"
            )
        lines.append("")

    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_file
