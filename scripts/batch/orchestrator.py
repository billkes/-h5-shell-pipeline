"""Batch orchestration for Flutter and mixed app production.

Git: init + per-phase commits run inside ``FlutterPipeline`` (see ``git_ops.py``).
Push uses ``task.csv`` ``仓库地址`` when the single-app run finishes.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from batch.batch_tag import ensure_output_layout, report_paths
from batch.config import BatchConfig, safe_dir_name
from batch.csv_tasks import (
    CsvTaskRow,
    app_workspace,
    repo_container_name,
)
from batch.pipeline import FlutterPipeline
from batch.pack_type import H5_FLUTTER_SHELL, H5_OC_SHELL, H5_SHELL, H5_SWIFT_SHELL
from batch.queue import QueueTask, VALID_TYPES, load_queue, parse_single_arg
from batch.flutter_ops import analyze_log_shows_success
from batch.batch_log import (
    batch_log_session,
    format_log_timestamp,
    make_batch_stamp,
)
from batch.batch_run_log import BatchRunLog, TaskRunContext, set_run_log, task_failure_headline
from batch.registry import ensure_contentpack_registry, find_package_by_name
from batch.report import generate_batch_report
from batch.state import (
    PM_PHASE,
    PM_UI_PLAN_PHASE,
    PROGRAMMER_PHASE,
    TEST_PHASE,
    UI_PHASE,
    phase_done,
    pipeline_complete,
    pipeline_version_from_data,
    read_state,
)
from batch.tool_delegate import TOOL_TYPES, run_tool_single

APP_PIPELINE_TYPES = frozenset(
    {
        H5_SHELL,
        H5_FLUTTER_SHELL,
        H5_SWIFT_SHELL,
        H5_OC_SHELL,
    }
)
FLUTTER_TYPES = APP_PIPELINE_TYPES  # legacy import/test alias


class BatchOrchestrator:
    """Coordinate multi-app batch runs.

    核心原则：批量跑就是逐个跑单个项目。
    ``run_single`` 负责一个项目；``run_mixed_batch`` 仅负责循环与汇总。
    """

    def __init__(self, cfg: BatchConfig) -> None:
        self.cfg = cfg
        self.flutter = FlutterPipeline(cfg)

    def _csv_row_for(self, task: QueueTask) -> CsvTaskRow:
        row = self.cfg.task_csv_by_name.get(task.name)
        if not isinstance(row, CsvTaskRow):
            raise RuntimeError(f"CSV 未找到任务行: {task.name}")
        return row

    def _resolve_workspace(self, output_base: Path, task: QueueTask) -> Path:
        """``output/{AppName}-Swift/{AppName}/`` etc. by pack_type."""
        row = self._csv_row_for(task)
        repo_name = repo_container_name(
            task.name, row.git_url, pack_type=task.pack_type
        )
        ws = app_workspace(output_base, repo_name, safe_dir_name(task.name))
        ws.mkdir(parents=True, exist_ok=True)
        return ws

    def _health_effectively_done(self, workspace: Path) -> bool:
        return phase_done(workspace, PROGRAMMER_PHASE) or analyze_log_shows_success(
            workspace / "analyze.log"
        )

    @staticmethod
    def _package_fully_complete(workspace: Path) -> bool:
        return pipeline_complete(workspace)

    def _is_v3_workspace(self, workspace: Path) -> bool:
        return pipeline_version_from_data(read_state(workspace)) != "v2"

    def _result_icon(self, workspace: Path, icon: str) -> str:
        if icon == "dry-run":
            return "🔵"
        if icon == "✅":
            return "✅"
        if self._is_v3_workspace(workspace):
            if phase_done(workspace, PROGRAMMER_PHASE):
                return "✅"
            if phase_done(workspace, PM_UI_PLAN_PHASE):
                return "🟡"
            return "❌"

        if phase_done(workspace, TEST_PHASE):
            return "✅"
        if phase_done(workspace, PROGRAMMER_PHASE):
            return "⚠️"
        if icon == "⚠️":
            return "⚠️"
        if icon == "🟡":
            return "🟡"
        if phase_done(workspace, UI_PHASE):
            return "⚠️"
        if phase_done(workspace, PM_PHASE):
            return "🟡"
        return "❌"

    def _format_result(self, task: QueueTask, workspace: Path, icon: str) -> str:
        sym = self._result_icon(workspace, icon)
        suffix = self._result_suffix(workspace, icon)
        return f"{sym}  {task.name}  （{suffix}）"

    def _result_suffix(self, workspace: Path, icon: str) -> str:
        if icon == "dry-run":
            return "dry-run"
        if self._is_v3_workspace(workspace):
            if phase_done(workspace, PROGRAMMER_PHASE):
                return "全流程完成"
            if phase_done(workspace, PM_UI_PLAN_PHASE):
                return "Plan 完成，Programmer 未完成"
            return "Plan 未完成"

        if phase_done(workspace, TEST_PHASE):
            return "全流程完成"
        if phase_done(workspace, PROGRAMMER_PHASE):
            return "Programmer 完成，测试未完成"
        if self._health_effectively_done(workspace):
            return "analyze 通过，测试未完成"
        if phase_done(workspace, UI_PHASE):
            return "UI 完成，Programmer 未完成"
        if phase_done(workspace, PM_PHASE):
            return "PM 完成，UI 未完成"
        return "PM 未完成"

    def run_single(
        self,
        task: QueueTask,
        output_base: Path,
        *,
        index: int = 1,
        total: int = 1,
    ) -> tuple[str, bool]:
        """Run a single task and return ``(result_line, failed)``.

        ``failed`` is ``True`` when the task should be recorded as failed
        or unsupported.
        """
        ws = self._resolve_workspace(output_base, task)
        app_started = time.time()
        run_log = BatchRunLog()
        run_log.task = TaskRunContext(
            index=index,
            total=total,
            name=task.name,
            pack_type=task.pack_type,
            workspace=ws,
            desc=task.desc or "",
        )
        set_run_log(run_log)
        run_log.queue(f"{task.pack_type} | 开始")
        run_log.detail(f"目录: {ws}")
        if task.desc:
            run_log.detail(f"描述: {task.desc}")

        ensure_contentpack_registry(self.cfg.contentpack_registry)
        registered = find_package_by_name(self.cfg.contentpack_registry, task.name)
        if (
            registered
            and not self.cfg.force_rerun
            and not (ws / ".build-state.json").is_file()
        ):
            reg_at = str(registered.get("registeredAt") or "?")
            print(
                f"  >>> 跳过：{task.name} 已在 contentpack-registry 登记"
                f"（{reg_at}），工作区无断点；使用 --force 重跑"
            )
            elapsed = int(time.time() - app_started)
            run_log.queue(f"跳过（已登记 · 无断点） ({elapsed}s)")
            run_log.flush_task_details()
            set_run_log(None)
            return f"⏭️  {task.name}  （已登记 · 跳过）", False

        if (
            not self.cfg.force_rerun
            and (ws / ".build-state.json").is_file()
            and self._package_fully_complete(ws)
        ):
            print("  >>> 跳过（全流程已完成）")
            elapsed = int(time.time() - app_started)
            run_log.queue(f"跳过（全流程已完成）✅ ({elapsed}s)")
            run_log.flush_task_details()
            set_run_log(None)
            return f"✅  {task.name}  （已跳过）", False

        if task.pack_type in TOOL_TYPES:
            if self.cfg.dry_run:
                print(
                    f"  [dry-run] 将调用 Python ToolPipeline "
                    f'"{task.name}|{task.desc}"'
                )
                print(
                    f"  结束: {format_log_timestamp()} "
                    f"(耗时 {int(time.time() - app_started)}s)"
                )
                return f"🔵  {task.name}  （dry-run）", False
            ok = run_tool_single(self.cfg, task, ws)
            print(
                f"  结束: {format_log_timestamp()} "
                f"(耗时 {int(time.time() - app_started)}s)"
            )
            if ok:
                return f"✅  {task.name}  （工具包完成）", False
            return f"❌  {task.name}  （工具包失败）", True

        if task.pack_type not in APP_PIPELINE_TYPES:
            print(f"  >>> 未知类型 {task.pack_type}，跳过")
            print(
                f"  结束: {format_log_timestamp()} "
                f"(耗时 {int(time.time() - app_started)}s)"
            )
            return f"❌  {task.name}  （未知类型）", True

        ctx = self.flutter.build_context(
            task.name,
            task.desc,
            task.pack_type,
            ws,
        )
        icon = self.flutter.run(ctx)
        result = self._format_result(task, ctx.workspace, icon)
        failed = result.startswith("❌")
        elapsed = int(time.time() - app_started)
        sym = self._result_icon(ctx.workspace, icon)
        run_log.queue(f"结束 {sym} ({elapsed}s) — {self._result_suffix(ctx.workspace, icon)}")
        if failed or sym in ("⚠️", "❌"):
            run_log.detail(task_failure_headline(ctx.workspace))
        run_log.flush_task_details()
        set_run_log(None)
        return result, failed

    def run_mixed_batch(
        self,
        tasks: list[QueueTask],
        output_base: Path | None = None,
        *,
        batch_stamp: str | None = None,
        log_header_lines: list[str] | None = None,
        log_path: Path | None = None,
        report_path: Path | None = None,
        batch_id: str = "",
    ) -> Path:
        if output_base is None:
            output_base = ensure_output_layout(self.cfg.output_dir)
        else:
            output_base = ensure_output_layout(output_base)

        stamp = batch_stamp or make_batch_stamp()
        if log_path is None or report_path is None:
            lp, rp = report_paths(
                self.cfg.output_dir,
                batch_id=batch_id or self.cfg.batch_id,
                stamp=stamp,
            )
            log_path = log_path or lp
            report_path = report_path or rp
        batch_wall_start = datetime.now()

        with batch_log_session(
            log_path,
            header_lines=log_header_lines,
            started_at=batch_wall_start,
            output_base=output_base,
        ):
            run_log = BatchRunLog()
            set_run_log(run_log)
            run_log.banner(f"H5 Shell 批量生产 · {len(tasks)} 个任务")
            run_log.queue(f"输出: {output_base}")
            run_log.queue(f"batchId: {batch_id or self.cfg.batch_id}")

            started_at = batch_wall_start.astimezone(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
            batch_start = time.time()
            results: list[str] = []
            failed: list[str] = []

            for i, task in enumerate(tasks, 1):
                result, is_failed = self.run_single(
                    task, output_base, index=i, total=len(tasks)
                )
                results.append(result)
                if is_failed:
                    failed.append(f"{task.pack_type}|{task.name}")

            elapsed = int(time.time() - batch_start)
            run_log.queue(f"队列结束 ({elapsed}s)")
            self._print_summary(
                results, elapsed, output_base=output_base, tasks=tasks
            )
            if generate_batch_report(
                output_base,
                started_at,
                report_path,
                detailed_log_file=log_path,
                batch_elapsed_s=elapsed,
                failed_tasks=failed,
            ):
                print(f"📄 报告: {report_path}")
                print(f"📄 日志: {log_path}")
            set_run_log(None)

        return output_base

    @staticmethod
    def _print_summary(
        results: list[str],
        elapsed: int,
        *,
        output_base: Path | None = None,
        tasks: list[QueueTask] | None = None,
    ) -> None:
        print("")
        print("═" * 56)
        print(f"  批次完成  |  {len(results)} 任务  |  耗时 {_fmt_elapsed(elapsed)}")
        print("═" * 56)

        if output_base is not None and tasks:
            print("")
            print("【一眼概览】")
            for task in tasks:
                try:
                    row = BatchOrchestrator._resolve_workspace_static(
                        output_base, task
                    )
                    print(f"  {task_failure_headline(row)}")
                except (RuntimeError, OSError):
                    print(f"  {task.name} — （无法读取状态）")

        print("")
        print("【结果】")
        for r in results:
            print(f"  {r}")

        done = sum(1 for r in results if r.startswith("✅"))
        warn = sum(1 for r in results if r.startswith("⚠️"))
        failed_count = sum(1 for r in results if r.startswith("❌"))
        print("")
        print(f"  ✅ {done}  ⚠️ {warn}  ❌ {failed_count}")

        if output_base is not None:
            pass
        print("═" * 56)

    @staticmethod
    def _resolve_workspace_static(output_base: Path, task: QueueTask) -> Path:
        """Resolve workspace path without BatchConfig (summary helper)."""
        for sf in output_base.rglob(".build-state.json"):
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if data.get("name") == task.name:
                return sf.parent
        raise RuntimeError(task.name)


def _fmt_elapsed(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60:02d}s"


def load_tasks_from_file(
    path: Path,
    default_type: str,
    single: str = "",
    *,
    csv_path: Path | None = None,
) -> list[QueueTask]:
    if single:
        return [parse_single_arg(single, default_type)]
    if csv_path is not None:
        from batch.csv_tasks import load_tasks_from_csv_and_queue

        tasks, _, _ = load_tasks_from_csv_and_queue(csv_path, path, default_type)
        return tasks
    return load_queue(path, default_type)


def assert_valid_default_type(default_type: str) -> None:
    if default_type not in VALID_TYPES:
        raise ValueError(
            f"默认类型必须是: {' | '.join(sorted(VALID_TYPES))}"
        )
