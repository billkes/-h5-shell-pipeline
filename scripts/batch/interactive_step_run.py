"""Interactive step-level run / resume / rerun for V3 pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

from batch.batch_tag import ensure_output_layout
from batch.config import BatchConfig
from batch.orchestrator import BatchOrchestrator
from batch.pipeline_steps import STEP_LABELS, parse_step_range, steps_for_run
from batch.pipeline_v3_runner import V3StepRunner, format_step_status_lines
from batch.queue import QueueTask
from batch.registry import find_package_by_name
from batch.state import read_state


def _require_tty() -> bool:
    if sys.stdin.isatty():
        return True
    print("错误: 需要交互式终端")
    return False


def resolve_task_workspace(cfg: BatchConfig, task: QueueTask) -> Path:
    output = ensure_output_layout(cfg.output_dir)
    return BatchOrchestrator(cfg)._resolve_workspace(output, task)


def print_step_status(cfg: BatchConfig, task: QueueTask) -> None:
    ws = resolve_task_workspace(cfg, task)
    ordered = steps_for_run(
        pack_type=task.pack_type,
    )
    print(f"\n当前项目: {task.name} ({task.pack_type})")
    print(f"工作区: {ws}")
    sf = ws / ".build-state.json"
    registered = find_package_by_name(cfg.contentpack_registry, task.name)
    if not sf.is_file():
        if registered:
            reg_at = str(registered.get("registeredAt") or "?")
            print(
                f"  （已登记 {reg_at}，工作区无断点 — "
                f"选「强制重跑指定步骤」可重跑范围，如 1-8）"
            )
        else:
            print("  （尚无 .build-state.json — 首次跑将自动创建）")
    print("")
    for line in format_step_status_lines(ws, ordered):
        print(line)
    print("")


def _interactive_select_steps(
    cfg: BatchConfig, task: QueueTask
) -> tuple[list[str] | None, bool, bool]:
    """Returns (step_ids, continue_from, rerun)."""
    ws = resolve_task_workspace(cfg, task)
    ordered = steps_for_run(
        pack_type=task.pack_type,
    )
    print_step_status(cfg, task)
    print("可选步骤（见上方编号）：")
    print("  输入编号 / 步骤 id / 范围（如 5 或 build.agent 或 7-10）")
    print("  continue — 从首个失败/未完成步骤继续")
    print("  rerun N / N-M — 强制重跑指定步或范围（重置状态）")
    print("  回车     — 取消")
    print("")
    raw = input("请选择: ").strip()
    if not raw:
        return None, False, False
    lower = raw.lower()
    if lower in ("continue", "c", "续跑", "继续"):
        return None, True, False
    if lower.startswith("rerun "):
        picked = parse_step_range(raw, ordered)
        if not picked:
            print("无效 rerun 输入")
            return None, False, False
        return picked, False, True
    picked = parse_step_range(raw, ordered)
    if not picked:
        print("无效输入")
        return None, False, False
    return picked, False, False


def interactive_run_mode(
    cfg: BatchConfig,
    tasks: list[QueueTask],
) -> tuple[list[QueueTask], BatchConfig]:
    """Prompt run mode; may narrow to single task for step modes."""
    print("")
    print("─" * 56)
    print("  产包模式（V3 · 占位图产包中生成 · 批次后自动本地渲染）")
    print("─" * 56)
    print("  [1] 一键跑完整包")
    print("  [2] 选择步骤跑")
    print("  [3] 从失败步骤继续")
    print("  [4] 查看当前断点状态")
    print("  [5] 强制重跑指定步骤（含范围，如 1-8）")
    print("  [6] 强制从头跑（完整包 · --force）")
    print("  [0] 返回 / 取消")
    print("")
    choice = input("请选择: ").strip()

    if choice in ("0", ""):
        return [], cfg

    if choice in ("1", "6"):
        cfg.pipeline_step_ids = None
        cfg.pipeline_step_continue = False
        cfg.pipeline_step_rerun = False
        cfg.force_rerun = choice == "6"
        return tasks, cfg

    if choice in ("2", "3", "5"):
        if len(tasks) > 1:
            print("\n步骤模式仅支持单包，请选择一个项目：")
            tasks = [_pick_one_task(tasks)]
        task = tasks[0]

        if choice == "3":
            print_step_status(cfg, task)
            cfg.pipeline_step_ids = None
            cfg.pipeline_step_continue = True
            cfg.pipeline_step_rerun = False
            return tasks, cfg

        if choice == "2":
            step_ids, cont, rerun = _interactive_select_steps(cfg, task)
            if step_ids is None and not cont:
                return [], cfg
            cfg.pipeline_step_ids = step_ids
            cfg.pipeline_step_continue = cont
            cfg.pipeline_step_rerun = rerun
            return tasks, cfg

        if choice == "5":
            print_step_status(cfg, task)
            raw = input(
                "重跑编号 / 步骤 id / 范围（如 5 或 1-8 或 sync.distilled）: "
            ).strip()
            ordered = steps_for_run(
                pack_type=task.pack_type,
            )
            picked = parse_step_range(f"rerun {raw}", ordered) if raw else []
            if not picked:
                print("无效输入")
                return [], cfg
            cfg.pipeline_step_ids = picked
            cfg.pipeline_step_continue = False
            cfg.pipeline_step_rerun = True
            return tasks, cfg

    if choice == "4":
        if len(tasks) > 1:
            tasks = [_pick_one_task(tasks)]
        print_step_status(cfg, tasks[0])
        input("按回车返回...")
        return interactive_run_mode(cfg, tasks)

    print("无效输入")
    return interactive_run_mode(cfg, tasks)


def _pick_one_task(tasks: list[QueueTask]) -> QueueTask:
    for idx, t in enumerate(tasks, start=1):
        print(f"  [{idx}] {t.name:20}  {t.pack_type}")
    while True:
        choice = input("编号或项目名: ").strip()
        if choice.isdigit():
            i = int(choice)
            if 1 <= i <= len(tasks):
                return tasks[i - 1]
        for t in tasks:
            if t.name == choice:
                return t
        print("无效输入")
