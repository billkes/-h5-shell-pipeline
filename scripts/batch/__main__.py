#!/usr/bin/env python3
"""CLI entry for h5-shell-pipeline batch scripts."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from batch.config import BatchConfig
from batch.csv_tasks import (
    init_empty_task_csv,
    load_csv_tasks,
    load_task_csv_raw,
    validate_task_csv,
)
from batch.pipeline import BuildContext, build_all, build_one, ensure_h5_bridge_drawn, print_summary
from batch.task_schema import STANDARD_COLUMNS, task_csv_path


def _csv_path(args: argparse.Namespace) -> Path:
    cfg = BatchConfig.from_env()
    return cfg.task_csv


def cmd_task_init(args: argparse.Namespace) -> int:
    path = _csv_path(args)
    if path.exists() and not args.force:
        print(f"❌ task.csv 已存在: {path}（加 --force 覆盖）")
        return 1
    init_empty_task_csv(path, batch_id=args.batch_id, row_count=args.rows)
    print(f"✅ 已创建 {path}（batchId={args.batch_id}, {args.rows} 行空行）")
    return 0


def cmd_task_add(args: argparse.Namespace) -> int:
    path = _csv_path(args)
    if not path.exists():
        print(f"❌ task.csv 不存在，先用 'task init' 创建: {path}")
        return 1
    from batch.csv_tasks import load_task_csv_raw, write_task_csv_rows

    meta, rows, fieldnames = load_task_csv_raw(path)
    for _ in range(args.rows):
        rows.append({c: "" for c in STANDARD_COLUMNS})
    write_task_csv_rows(path, meta, rows, fieldnames=fieldnames)
    print(f"✅ 已在 {path} 追加 {args.rows} 行空行（共 {len(rows)} 行）")
    return 0


def cmd_task_validate(args: argparse.Namespace) -> int:
    path = _csv_path(args)
    try:
        validate_task_csv(path)
        print(f"✅ {path} 校验通过")
        return 0
    except Exception as exc:
        print(f"❌ {path} 校验失败: {exc}")
        return 1


def cmd_task_list(args: argparse.Namespace) -> int:
    path = _csv_path(args)
    from batch.csv_tasks import load_task_csv_raw

    try:
        meta, raw_rows, _ = load_task_csv_raw(path)
    except Exception as exc:
        print(f"❌ 读取失败: {exc}")
        return 1
    if not raw_rows:
        print("（无任务）")
        return 0
    print(f"{'#':<4} {'应用主名称':<16} {'应用类型':<16} {'编程风格':<10} {'命名混淆规则':<14}")
    print("-" * 64)
    valid = 0
    for idx, raw in enumerate(raw_rows, start=1):
        name = raw.get("应用主名称", "").strip()
        if name:
            valid += 1
        print(
            f"{idx:<4} {name or '(空)':<16} "
            f"{raw.get('应用类型', '').strip() or '-':<16} "
            f"{raw.get('编程风格', '').strip() or '-':<10} "
            f"{raw.get('命名混淆规则', '').strip() or '-':<14}"
        )
    print(f"\n共 {len(raw_rows)} 行，有效 {valid} 个任务")
    return 0


def cmd_task_show(args: argparse.Namespace) -> int:
    path = _csv_path(args)
    try:
        rows = load_csv_tasks(path)
    except Exception as exc:
        print(f"❌ 读取失败: {exc}")
        return 1
    for row in rows:
        if row.name == args.name:
            print(f"应用主名称: {row.name}")
            print(f"全称: {row.full_name}")
            print(f"应用类型: {row.pack_type}")
            print(f"编程风格: {row.programming_style}")
            print(f"命名混淆规则: {row.naming_obfuscation_rule}")
            print(f"架构模式: {row.architecture_pattern}")
            print(f"状态管理: {row.state_management}")
            print(f"首个商品Code: {row.first_product_code}")
            print(f"仓库地址: {row.git_url}")
            print(f"协议风格: {row.privacy_style}")
            print(f"隐私文件: {row.privacy_file}")
            print(f"webviewEngine: {row.webview_engine}")
            print(f"bridgeCallStyle: {row.bridge_call_style}")
            print(f"mediaServe: {row.media_serve}")
            return 0
    print(f"❌ 未找到任务: {args.name}")
    return 1


def cmd_task_ready(args: argparse.Namespace) -> int:
    """Pre-build readiness check (strict extended validation).

    Automatically draws/reuses Bridge 七维 for h5 shells before validating,
    so the CSV is left in a build-ready state on success.
    """
    path = _csv_path(args)
    ctx = _build_context(args)
    ensure_h5_bridge_drawn(ctx)
    # Auto-fill productFlow for rows that have theme fields but empty productFlow
    from batch.csv_tasks import fill_product_flow_to_csv

    fill_product_flow_to_csv(path)
    try:
        rows = load_csv_tasks(path, strict_extended=True, project_dir=PROJECT_ROOT)
    except Exception as exc:
        print(f"❌ {path} 未就绪: {exc}")
        return 1
    print(f"✅ {path} 已就绪（{len(rows)} 个任务）")
    return 0


def cmd_task_fill_flow(args: argparse.Namespace) -> int:
    """Fill empty productFlow cells with template-generated values."""
    path = _csv_path(args)
    from batch.csv_tasks import fill_product_flow_to_csv

    try:
        filled = fill_product_flow_to_csv(path)
    except Exception as exc:
        print(f"❌ 填充失败: {exc}")
        return 1
    if filled:
        print(f"✅ 已填充 productFlow: {', '.join(filled)}")
    else:
        print("✅ 所有行已有 productFlow，无需填充")
    return 0


def _build_context(args: argparse.Namespace) -> BuildContext:
    cfg = BatchConfig.from_env()
    batch_id = getattr(args, "batch_id", "") or cfg.batch_id
    if not batch_id:
        meta, _, _ = load_task_csv_raw(cfg.task_csv)
        batch_id = meta.batch_id or "BATCH-0000"
    output_root = cfg.output_dir / batch_id
    return BuildContext(
        cfg=cfg,
        batch_id=batch_id,
        output_root=output_root,
        h5_host=getattr(args, "h5_host", "") or os.environ.get("H5_PROD_HOST", ""),
        team_id=getattr(args, "team_id", "") or os.environ.get("APPLE_TEAM_ID", ""),
    )


def cmd_build_all(args: argparse.Namespace) -> int:
    ctx = _build_context(args)
    try:
        results = build_all(ctx)
    except Exception as exc:
        print(f"❌ 构建失败: {exc}")
        return 1
    return print_summary(results)


def cmd_build_one(args: argparse.Namespace) -> int:
    ctx = _build_context(args)
    ensure_h5_bridge_drawn(ctx)
    try:
        rows = load_csv_tasks(ctx.cfg.task_csv, strict_extended=True, project_dir=PROJECT_ROOT)
    except Exception as exc:
        print(f"❌ 读取 task.csv 失败: {exc}")
        return 1
    for row in rows:
        if row.name == args.name:
            result = build_one(ctx, row)
            return print_summary([result])
    print(f"❌ 未找到任务: {args.name}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m batch",
        description="h5-shell-pipeline batch task CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # task init
    p_init = sub.add_parser("task-init", help="创建空 task.csv")
    p_init.add_argument("--batch-id", required=True, help="批次 ID")
    p_init.add_argument("--rows", type=int, default=1, help="空行数")
    p_init.add_argument("--force", action="store_true", help="覆盖已存在文件")
    p_init.set_defaults(func=cmd_task_init)

    # task add
    p_add = sub.add_parser("task-add", help="向 task.csv 追加空行")
    p_add.add_argument("--rows", type=int, default=1, help="追加行数")
    p_add.set_defaults(func=cmd_task_add)

    # task validate
    p_validate = sub.add_parser("task-validate", help="校验 task.csv")
    p_validate.set_defaults(func=cmd_task_validate)

    # task list
    p_list = sub.add_parser("task-list", help="列出所有任务")
    p_list.set_defaults(func=cmd_task_list)

    # task show
    p_show = sub.add_parser("task-show", help="查看单个任务")
    p_show.add_argument("name", help="应用主名称")
    p_show.set_defaults(func=cmd_task_show)

    # task ready
    p_ready = sub.add_parser("task-ready", help="产包前严格校验")
    p_ready.set_defaults(func=cmd_task_ready)

    # task fill-flow
    p_fill_flow = sub.add_parser("task-fill-flow", help="自动填充 productFlow")
    p_fill_flow.set_defaults(func=cmd_task_fill_flow)

    # build all
    p_build_all = sub.add_parser("build-all", help="构建全部任务")
    p_build_all.add_argument("--batch-id", help="批次 ID（默认从 task.csv 读取）")
    p_build_all.add_argument("--h5-host", help="H5 生产域名")
    p_build_all.add_argument("--team-id", help="Apple Team ID")
    p_build_all.set_defaults(func=cmd_build_all)

    # build one
    p_build_one = sub.add_parser("build", help="构建单个任务")
    p_build_one.add_argument("name", help="应用主名称")
    p_build_one.add_argument("--batch-id", help="批次 ID（默认从 task.csv 读取）")
    p_build_one.add_argument("--h5-host", help="H5 生产域名")
    p_build_one.add_argument("--team-id", help="Apple Team ID")
    p_build_one.set_defaults(func=cmd_build_one)

    return parser


def main(argv: list[str] | None = None) -> int:
    # 无参数 → 交互式菜单
    if argv is None and len(sys.argv) <= 1:
        from batch.interactive_menu import interactive_main

        return interactive_main()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
