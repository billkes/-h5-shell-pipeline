"""Task preparation CLI for h5-shell-pipeline (no Feishu dependency)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from batch.config import BatchConfig
from batch.csv_tasks import init_empty_task_csv, load_task_csv_meta
from batch.task_add import run_task_fill_simple
from batch.task_audit import audit_task_csv
from batch.task_schema import TASK_CSV_FILENAME, task_csv_path


def _resolve_csv(raw: Path | None, cfg: BatchConfig) -> Path:
    return (raw or cfg.task_csv).resolve()


def cmd_init(args: argparse.Namespace, cfg: BatchConfig) -> int:
    path = _resolve_csv(args.csv, cfg)
    if path.is_file() and not args.force:
        print(f"错误: {path} 已存在，使用 --force 覆盖", file=sys.stderr)
        return 1
    init_empty_task_csv(path, batch_id=args.batch_id, row_count=args.rows)
    print(f">>> 已创建 {path} · batchId={args.batch_id} · {args.rows} 空行")
    return 0


def cmd_add(args: argparse.Namespace, cfg: BatchConfig) -> int:
    from batch.csv_tasks import load_task_csv_raw, write_task_csv_rows
    from batch.task_schema import STANDARD_COLUMNS

    path = _resolve_csv(args.csv, cfg)
    if not path.is_file():
        print(f"错误: task.csv 不存在: {path}", file=sys.stderr)
        return 1
    meta, rows, fieldnames = load_task_csv_raw(path)
    for _ in range(args.count):
        rows.append({c: "" for c in STANDARD_COLUMNS})
    write_task_csv_rows(path, meta, rows, fieldnames=fieldnames)
    print(f">>> 已追加 {args.count} 空行（共 {len(rows)} 行）· batchId={meta.batch_id}")
    return 0


def cmd_fill(args: argparse.Namespace, cfg: BatchConfig) -> int:
    path = _resolve_csv(args.csv, cfg)
    if not path.is_file():
        print(f"错误: task.csv 不存在: {path}", file=sys.stderr)
        return 1
    meta = load_task_csv_meta(path)
    batch_id = args.batch_id or meta.batch_id
    try:
        run_task_fill_simple(path, cfg, batch_id=batch_id, force=args.force)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    print(f">>> fill 完成: Bridge 七维 + productFlow → {path}")
    return 0


def cmd_audit(args: argparse.Namespace, cfg: BatchConfig) -> int:
    path = _resolve_csv(args.csv, cfg)
    registry = cfg.registry_dir / "h5-shell-registry.json"
    ok, issues, soft = audit_task_csv(path, registry, check_feishu=False)
    if soft:
        print("单维使用分布提示（不阻断）:")
        for item in soft:
            print(f"  ~ {item}")
    if ok:
        print(f">>> audit 通过: {path}")
        return 0
    print("audit 未通过:")
    for item in issues:
        print(f"  ! {item}")
    return 1


def cmd_ready(args: argparse.Namespace, cfg: BatchConfig) -> int:
    from batch.batch_firewall import validate_batch_firewall

    path = _resolve_csv(args.csv, cfg)
    cfg.task_csv_path = path
    meta = load_task_csv_meta(path)
    cfg.batch_id = meta.batch_id
    ok = validate_batch_firewall(cfg, csv_path=path, skip_feishu=True)
    return 0 if ok else 1


def cmd_validate(args: argparse.Namespace, cfg: BatchConfig) -> int:
    from batch.csv_tasks import validate_task_csv

    path = _resolve_csv(args.csv, cfg)
    try:
        validate_task_csv(path)
        print(f">>> validate 通过: {path}")
        return 0
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace, cfg: BatchConfig) -> int:
    from batch.csv_tasks import load_task_csv_raw

    path = _resolve_csv(args.csv, cfg)
    try:
        _, raw_rows, _ = load_task_csv_raw(path)
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    if not raw_rows:
        print("（无任务）")
        return 0
    print(f"{'#':<4} {'应用主名称':<16} {'应用类型':<16} {'编程风格':<10}")
    print("-" * 50)
    for idx, raw in enumerate(raw_rows, start=1):
        name = raw.get("应用主名称", "").strip() or "(空)"
        print(
            f"{idx:<4} {name:<16} "
            f"{raw.get('应用类型', '').strip() or '-':<16} "
            f"{raw.get('编程风格', '').strip() or '-':<10}"
        )
    print(f"\n共 {len(raw_rows)} 行")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cfg = BatchConfig.from_env()
    parser = argparse.ArgumentParser(prog="batch task", description="task.csv 准备阶段")
    parser.add_argument("--csv", type=Path, default=None, help=f"默认 {TASK_CSV_FILENAME}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="创建空 task.csv")
    p_init.add_argument("--batch-id", required=True)
    p_init.add_argument("--rows", type=int, default=1)
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add", help="追加 N 行空任务")
    p_add.add_argument("--count", type=int, default=1)
    p_add.set_defaults(func=cmd_add)

    p_fill = sub.add_parser("fill", help="抽 Bridge 七维 + productFlow")
    p_fill.add_argument("--batch-id", default="")
    p_fill.add_argument("--force", action="store_true")
    p_fill.set_defaults(func=cmd_fill)

    p_audit = sub.add_parser("audit", help="批次审计（多样性 + 必填）")
    p_audit.set_defaults(func=cmd_audit)

    p_ready = sub.add_parser("ready", help="产包前严格校验")
    p_ready.set_defaults(func=cmd_ready)

    p_validate = sub.add_parser("validate", help="基础格式校验")
    p_validate.set_defaults(func=cmd_validate)

    p_list = sub.add_parser("list", help="列出任务")
    p_list.set_defaults(func=cmd_list)

    # Legacy hyphen aliases
    for name, target in (
        ("task-init", "init"),
        ("task-add", "add"),
        ("task-fill", "fill"),
        ("task-audit", "audit"),
        ("task-ready", "ready"),
        ("task-validate", "validate"),
        ("task-list", "list"),
    ):
        p = sub.add_parser(name, help=f"alias for {target}")
        if target == "init":
            p.add_argument("--batch-id", required=True)
            p.add_argument("--rows", type=int, default=1)
            p.add_argument("--force", action="store_true")
        elif target == "add":
            p.add_argument("--count", type=int, default=1)
            p.add_argument("--rows", type=int, default=1)
        elif target == "fill":
            p.add_argument("--batch-id", default="")
            p.add_argument("--force", action="store_true")
        p.set_defaults(func=globals()[f"cmd_{target}"])

    args = parser.parse_args(argv)
    if hasattr(args, "rows") and args.command in ("task-add", "add"):
        args.count = getattr(args, "count", None) or args.rows
    return args.func(args, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
