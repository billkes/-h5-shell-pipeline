#!/usr/bin/env python3
"""CLI entry for billkes batch production."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from batch.config import _scripts_root  # noqa: E402

SCRIPTS_ROOT = _scripts_root()
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from batch.batch_log import batch_log_session
from batch.batch_runs import append_batch_run, batch_runs_path
from batch.batch_tag import ensure_output_layout, make_batch_stamp, report_paths
from batch.config import BatchConfig
from batch.csv_tasks import app_workspace_registry_entry, load_task_csv_meta, load_tasks_for_run
from batch.orchestrator import BatchOrchestrator
from batch.queue import QueueTask
from batch.task_schema import TASK_CSV_FILENAME


def _build_parser(prog: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=prog,
        description=f"批量生产（默认读取根目录 {TASK_CSV_FILENAME}）",
        add_help=True,
    )
    p.add_argument(
        "--csv",
        dest="csv_path",
        default=None,
        metavar="PATH",
        help=f"任务台账（默认项目根 {TASK_CSV_FILENAME}）",
    )
    p.add_argument(
        "--name",
        dest="app_name",
        default=None,
        metavar="NAME",
        help="只跑指定应用名的项目",
    )
    p.add_argument(
        "--row",
        dest="row_number",
        type=int,
        default=None,
        metavar="N",
        help="只跑 CSV 第 N 行（1 开始）",
    )
    p.add_argument(
        "--legacy-pipeline",
        dest="legacy_pipeline",
        action="store_true",
        help="维护者：V2 四角色流水线 (PM/UI/Programmer/Tester)",
    )
    p.add_argument(
        "--force",
        dest="force_rerun",
        action="store_true",
        help="重置 .build-state.json，从头跑",
    )
    p.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="只打印将执行的 Phase，不调用 Agent",
    )
    p.add_argument(
        "--agent-provider",
        dest="agent_provider",
        default=None,
        choices=("cursor", "iflow"),
        help="Agent 调用方式：cursor（默认）或 iflow",
    )
    return p


def _filter_tasks(
    tasks: list[QueueTask],
    app_name: str | None,
    row_number: int | None,
) -> list[QueueTask]:
    if row_number is not None:
        if not 1 <= row_number <= len(tasks):
            raise ValueError(f"行号 {row_number} 超出范围（1-{len(tasks)}）")
        return [tasks[row_number - 1]]
    if app_name:
        matches = [t for t in tasks if t.name == app_name]
        if not matches:
            raise ValueError(f"未找到项目: {app_name}")
        return matches
    return tasks


def _print_banner(title: str = "h5-shell-pipeline · 产包") -> None:
    print("")
    print("═" * 56)
    print(f"  {title}")
    print("═" * 56)


def _interactive_batch_run(*, show_banner: bool = True) -> int:
    """Fully interactive batch run — no CLI flags required."""
    if show_banner:
        _print_banner()

    cfg = BatchConfig.from_env()
    csv_path = cfg.task_csv.resolve()
    default_pack_type = cfg.batch_pack_type or "h5_swift_shell"

    try:
        tasks, csv_rows = load_tasks_for_run(
            csv_path,
            default_pack_type,
            project_dir=cfg.project_dir,
        )
        meta = load_task_csv_meta(csv_path)
    except (OSError, ValueError) as exc:
        print(f"错误: {exc}")
        return 1

    if not tasks:
        print("错误: task.csv 中没有可执行的项目")
        print("提示: 返回主菜单 → [2] 批次准备")
        return 1

    batch_id = meta.batch_id or "unknown"
    print(f"  批次 batchId: {batch_id}")
    print(f"  任务台账: {csv_path}（{len(csv_rows)} 行）")
    print("")

    if not sys.stdin.isatty():
        print("错误: 需要交互式终端，请直接运行 ./run.sh")
        return 1

    # 交互式选择 Agent provider
    env_provider = os.environ.get("AGENT_PROVIDER", cfg.agent_provider or "cursor")
    print(f"当前 Agent provider: {env_provider}")
    print("  [1] Cursor CLI")
    print("  [2] iFlow SDK")
    print("  回车  保持当前设置")
    provider_choice = input("请选择 Agent 调用方式: ").strip()
    chosen_provider = env_provider
    if provider_choice == "1":
        chosen_provider = "cursor"
    elif provider_choice == "2":
        chosen_provider = "iflow"
    if chosen_provider != env_provider:
        print(f"  → 本次使用: {chosen_provider}")
    print("")

    tasks = _select_run_scope(tasks)

    # 交互产包固定 V3；真图开关仅看 task.csv「真图」列
    cfg = BatchConfig.from_env(
        dry_run=False,
        legacy_pipeline=False,
        force_rerun=False,
        agent_provider=chosen_provider,
    )

    cfg.task_csv_path = csv_path
    cfg.task_csv_by_name = {r.name: r for r in csv_rows}
    cfg.batch_id = batch_id

    from batch.interactive_step_run import interactive_run_mode

    tasks, cfg = interactive_run_mode(cfg, tasks)
    if not tasks:
        return 0

    return _execute_batch_run(cfg, tasks, csv_path, csv_rows, meta)


def _execute_batch_run(
    cfg: BatchConfig,
    tasks: list[QueueTask],
    csv_path: Path,
    csv_rows: list,
    meta: object,
) -> int:
    batch_id = getattr(meta, "batch_id", None) or cfg.batch_id or "unknown"

    print(f"batchId: {batch_id}")
    print(f"任务台账: {csv_path}（{len(csv_rows)} 行）")
    if len(tasks) == 1:
        print(f"本次执行: {tasks[0].name}（{tasks[0].pack_type}）")
    else:
        print(f"本次执行: {len(tasks)} 个项目")
    print("")

    output = ensure_output_layout(cfg.output_dir)
    batch_stamp = make_batch_stamp()
    log_path, report_path = report_paths(
        cfg.output_dir, batch_id=batch_id, stamp=batch_stamp
    )

    log_header = [
        f"batchId: {batch_id}",
        f"任务台账: {csv_path}（{len(csv_rows)} 行）",
        f"本次执行: {len(tasks)} 个项目"
        if len(tasks) != 1
        else f"本次执行: {tasks[0].name}（{tasks[0].pack_type}）",
        f"输出目录: {output}（{{AppName}}-Swift / -OC / -Flutter / {{AppName}}/）",
        f"报告目录: {log_path.parent}",
    ]

    append_batch_run(
        batch_runs_path(cfg.registry_dir),
        batch_id=batch_id,
        stamp=batch_stamp,
        task_csv=str(csv_path),
        app_names=[t.name for t in tasks],
        output_dir=str(output),
        reports_dir=str(log_path.parent),
        app_workspaces=[
            app_workspace_registry_entry(
                output,
                name=t.name,
                pack_type=t.pack_type,
                git_url=(
                    (cfg.task_csv_by_name.get(t.name).git_url or "")
                    if cfg.task_csv_by_name.get(t.name)
                    else ""
                ),
            )
            for t in tasks
        ],
    )

    orch = BatchOrchestrator(cfg)
    try:
        orch.run_mixed_batch(
            tasks,
            output,
            batch_stamp=batch_stamp,
            log_header_lines=log_header,
            log_path=log_path,
            report_path=report_path,
            batch_id=batch_id,
        )
    except RuntimeError as exc:
        print(f"错误: {exc}")
        return 1

    return 0


def _select_run_scope(tasks: list[QueueTask]) -> list[QueueTask]:
    print("")
    print("执行范围：")
    print(f"  [1] 全部跑（{len(tasks)} 个项目）")
    print("  [2] 单独跑一个项目")
    print("")
    while True:
        choice = input("请选择: ").strip()
        if choice == "1":
            return tasks
        if choice == "2":
            return [_select_one_task(tasks)]
        print("无效输入，请重新选择")


def _select_one_task(tasks: list[QueueTask]) -> QueueTask:
    print("项目列表：")
    for idx, t in enumerate(tasks, start=1):
        desc = (t.desc or "")[:36]
        print(f"  [{idx}] {t.name:20}  {t.pack_type:12}  {desc}")
    print("")
    while True:
        choice = input("请输入编号或项目名: ").strip()
        if not choice:
            continue
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(tasks):
                return tasks[idx - 1]
        for t in tasks:
            if t.name == choice:
                return t
        print("无效输入，请重新选择")


def _sync_assets_main(argv: list[str]) -> int:
    import argparse
    from batch.config import BatchConfig
    from batch.image_prompts_sync import sync_image_prompt_assets

    parser = argparse.ArgumentParser(prog="batch sync-assets")
    parser.add_argument("flutter_dirs", nargs="+", metavar="FLUTTER_DIR")
    args = parser.parse_args(argv)
    cfg = BatchConfig.from_env()
    total = 0
    for raw in args.flutter_dirs:
        flutter_dir = Path(raw).expanduser().resolve()
        if not (flutter_dir / "pubspec.yaml").is_file():
            print(f"跳过 {flutter_dir}: 不是 Flutter 项目根")
            continue
        report = sync_image_prompt_assets(flutter_dir, cfg.project_dir)
        total += report.repaired
    print(f"\n合计补全: {total}")
    return 0


def _generate_assets_main(argv: list[str]) -> int:
    import argparse
    from batch.config import BatchConfig
    from batch.cursor_runner import run_agent
    from batch.flutter_ops import download_all_workspace_images, find_flutter_project
    from batch.pack_type import is_h5_shell
    from batch.phase9_asset_gate import phase9_asset_gate_passes
    from batch.prompts import PromptBuilder
    from batch.visual_lock_assets import fill_visual_lock_assets

    parser = argparse.ArgumentParser(prog="batch generate-assets")
    parser.add_argument(
        "workspaces",
        nargs="+",
        metavar="WORKSPACE_OR_FLUTTER_DIR",
        help="包工作区根，或 Flutter 工程根（含 pubspec.yaml）",
    )
    parser.add_argument("--name", dest="app_name", default=None)
    parser.add_argument("--desc", dest="app_desc", default="")
    args = parser.parse_args(argv)
    cfg = BatchConfig.from_env()
    prompts = PromptBuilder(cfg)
    ok_count = 0
    targets = [Path(raw).expanduser().resolve() for raw in args.workspaces]
    for root in targets:
        if (root / "pubspec.yaml").is_file():
            flutter_dir = root
            ws = root.parent if (root.parent / "本包登记信息.json").is_file() else root
        elif (root / "本包登记信息.json").is_file() or (root / "本包维度锁.json").is_file():
            ws = root
            flutter_dir = find_flutter_project(ws) or ws
        else:
            print(f"跳过 {root}: 不是包工作区或 Flutter 根")
            continue
        app_name = args.app_name or ws.name.split("-")[0] or ws.name
        pack_type = ""
        reg = ws / "本包登记信息.json"
        if reg.is_file():
            try:
                import json

                pack_type = str(
                    json.loads(reg.read_text(encoding="utf-8")).get("packType") or ""
                )
            except json.JSONDecodeError:
                pack_type = ""
        h5 = is_h5_shell(pack_type) or bool(
            (ws / "本包维度锁.json").is_file()
        )
        download_all_workspace_images(
            cfg,
            ws,
            flutter_dir,
            app_name,
            h5_shell=h5,
        )
        if (ws / "本包视觉锁.json").is_file() and not h5:
            fill_visual_lock_assets(ws, flutter_dir, app_name)
        assets_root = (
            flutter_dir if (flutter_dir / "image_prompts.json").is_file() else ws
        )
        agent_ok = run_agent(
            cfg,
            ws,
            prompts.asset_generator_phase(name=app_name, desc=args.app_desc),
        )
        if agent_ok and phase9_asset_gate_passes(assets_root):
            ok_count += 1
    print(f"\n合计通过: {ok_count}/{len(targets)}")
    return 0 if ok_count == len(targets) else 1


def _fetch_assets_main(argv: list[str]) -> int:
    import argparse
    from batch.config import BatchConfig
    from batch.fetch_prompt_assets import fetch_prompt_assets
    from batch.image_prompts_sync import sync_image_prompt_assets

    parser = argparse.ArgumentParser(prog="batch fetch-assets")
    parser.add_argument("flutter_dirs", nargs="+", metavar="FLUTTER_DIR")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    cfg = BatchConfig.from_env()
    total = 0
    for raw in args.flutter_dirs:
        flutter_dir = Path(raw).expanduser().resolve()
        if not (flutter_dir / "pubspec.yaml").is_file():
            continue
        report = fetch_prompt_assets(flutter_dir, cfg, force=args.force)
        total += report.fetched
        sync_image_prompt_assets(flutter_dir, cfg.project_dir)
    print(f"\n合计拉取: {total}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    if not argv:
        from batch.interactive_menu import interactive_main

        return interactive_main()

    if argv and argv[0] == "task":
        from batch.task_cli import main as task_main

        return task_main(argv[1:])
    if argv and argv[0] == "build":
        from batch.template_build import cmd_build_cli

        return cmd_build_cli(argv[1:])
    if argv and argv[0] == "h5-post":
        from batch.h5_post_delivery import main as h5_post_main

        return h5_post_main(argv[1:])
    if argv and argv[0] == "sync-assets":
        from batch.cli import _sync_assets_main

        return _sync_assets_main(argv[1:])
    if argv and argv[0] == "fetch-assets":
        from batch.cli import _fetch_assets_main

        return _fetch_assets_main(argv[1:])
    if argv and argv[0] in (
        "task-init", "task-add", "task-validate", "task-list",
        "task-ready", "task-fill-flow", "task-show", "task-compose-theme", "build-all",
    ):
        from batch.legacy_cli import main as legacy_main

        return legacy_main(argv)
    if argv and argv[0] == "feishu":
        print("错误: h5-shell-pipeline 未接入飞书，请人工维护 task.csv")
        return 1
    if argv and argv[0].startswith("migrate-"):
        print(f"错误: 不支持命令 {argv[0]}")
        return 1
    if argv and argv[0] == "generate-assets":
        from batch.cli import _generate_assets_main

        return _generate_assets_main(argv[1:])

    prog = Path(sys.argv[0]).name
    args = _build_parser(prog).parse_args(argv)

    cfg = BatchConfig.from_env(
        dry_run=args.dry_run,
        legacy_pipeline=args.legacy_pipeline,
        force_rerun=args.force_rerun,
        agent_provider=args.agent_provider or os.environ.get("AGENT_PROVIDER", "cursor"),
    )
    default_pack_type = cfg.batch_pack_type or "h5_swift_shell"
    csv_path = Path(args.csv_path).expanduser() if args.csv_path else cfg.task_csv
    csv_path = csv_path.resolve()

    try:
        tasks, csv_rows = load_tasks_for_run(
            csv_path,
            default_pack_type,
            project_dir=cfg.project_dir,
        )
        meta = load_task_csv_meta(csv_path)
    except (OSError, ValueError) as exc:
        print(f"错误: {exc}")
        return 1

    cfg.task_csv_path = csv_path
    cfg.task_csv_by_name = {r.name: r for r in csv_rows}
    cfg.batch_id = meta.batch_id

    try:
        if args.app_name or args.row_number is not None:
            tasks = _filter_tasks(tasks, args.app_name, args.row_number)
        elif sys.stdin.isatty():
            tasks = _select_run_scope(tasks)
    except ValueError as exc:
        print(f"错误: {exc}")
        return 1

    if not tasks:
        print("错误: 没有可执行的项目")
        return 1

    return _execute_batch_run(cfg, tasks, csv_path, csv_rows, meta)


if __name__ == "__main__":
    raise SystemExit(main())
