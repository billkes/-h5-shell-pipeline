#!/usr/bin/env python3
"""Legacy hyphenated CLI commands (task-init, build-all, etc.)."""

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
from batch.template_build import (
    BuildContext,
    build_all,
    build_one,
    ensure_h5_bridge_drawn,
    print_summary,
)
from batch.task_schema import STANDARD_COLUMNS


def _csv_path(args: argparse.Namespace) -> Path:
    return BatchConfig.from_env().task_csv


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
        print(f"❌ task.csv 不存在: {path}")
        return 1
    from batch.csv_tasks import write_task_csv_rows

    meta, rows, fieldnames = load_task_csv_raw(path)
    for _ in range(args.rows):
        rows.append({c: "" for c in STANDARD_COLUMNS})
    write_task_csv_rows(path, meta, rows, fieldnames=fieldnames)
    print(f"✅ 已追加 {args.rows} 行（共 {len(rows)} 行）")
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
    try:
        _, raw_rows, _ = load_task_csv_raw(path)
    except Exception as exc:
        print(f"❌ 读取失败: {exc}")
        return 1
    if not raw_rows:
        print("（无任务）")
        return 0
    print(f"{'#':<4} {'应用主名称':<16} {'应用类型':<16}")
    print("-" * 40)
    for idx, raw in enumerate(raw_rows, start=1):
        print(
            f"{idx:<4} {raw.get('应用主名称', '').strip() or '(空)':<16} "
            f"{raw.get('应用类型', '').strip() or '-':<16}"
        )
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
            print(f"应用类型: {row.pack_type}")
            print(f"webviewEngine: {row.webview_engine}")
            return 0
    print(f"❌ 未找到: {args.name}")
    return 1


def cmd_task_ready(args: argparse.Namespace) -> int:
    from batch.batch_firewall import validate_batch_firewall

    cfg = BatchConfig.from_env()
    path = _csv_path(args)
    cfg.task_csv_path = path
    meta, _, _ = load_task_csv_raw(path)
    cfg.batch_id = meta.batch_id
    ensure_h5_bridge_drawn(_build_context(argparse.Namespace()))
    from batch.csv_tasks import fill_product_flow_to_csv

    fill_product_flow_to_csv(path)
    return 0 if validate_batch_firewall(cfg, csv_path=path, skip_feishu=True) else 1


def cmd_task_fill_flow(args: argparse.Namespace) -> int:
    from batch.csv_tasks import fill_product_flow_to_csv

    path = _csv_path(args)
    filled = fill_product_flow_to_csv(path)
    print(f"✅ productFlow: {', '.join(filled) if filled else '无需填充'}")
    return 0


def _build_context(args: argparse.Namespace) -> BuildContext:
    cfg = BatchConfig.from_env()
    meta, _, _ = load_task_csv_raw(cfg.task_csv)
    batch_id = getattr(args, "batch_id", "") or meta.batch_id or "BATCH-0000"
    return BuildContext(
        cfg=cfg,
        batch_id=batch_id,
        output_root=cfg.output_dir / batch_id,
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


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        return 1
    cmd = argv[0]
    rest = argv[1:]
    parser = argparse.ArgumentParser()
    if cmd == "task-init":
        parser.add_argument("--batch-id", required=True)
        parser.add_argument("--rows", type=int, default=1)
        parser.add_argument("--force", action="store_true")
        return cmd_task_init(parser.parse_args(rest))
    if cmd == "task-add":
        parser.add_argument("--rows", type=int, default=1)
        return cmd_task_add(parser.parse_args(rest))
    if cmd in ("task-validate", "task-list", "task-fill-flow"):
        return {"task-validate": cmd_task_validate, "task-list": cmd_task_list,
                "task-fill-flow": cmd_task_fill_flow}[cmd](parser.parse_args(rest))
    if cmd == "task-ready":
        return cmd_task_ready(parser.parse_args(rest))
    if cmd == "task-show":
        parser.add_argument("name")
        return cmd_task_show(parser.parse_args(rest))
    if cmd == "build-all":
        parser.add_argument("--batch-id", default="")
        parser.add_argument("--h5-host", default="")
        parser.add_argument("--team-id", default="")
        return cmd_build_all(parser.parse_args(rest))
    print(f"未知命令: {cmd}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
