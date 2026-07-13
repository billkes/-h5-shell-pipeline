"""CLI: ``python3 -m batch feishu check-env | prod-a check``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from batch.feishu_config import default_feishu_config_path, load_feishu_config
from batch.feishu_env_checker import run_check
from batch.feishu_prod_a import probe_prod_a_registry
from batch.feishu_theme_sync import (
    fetch_available_theme_index,
    probe_theme_library_index,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="飞书 / lark-cli 环境检测与产 A 拉取")
    sub = parser.add_subparsers(dest="command")

    check = sub.add_parser("check-env", help="检查 lark-cli 安装、登录与只读 scope")
    check.add_argument(
        "--config",
        default=None,
        help=f"feishu 配置（默认 {default_feishu_config_path()}）",
    )

    prod_a = sub.add_parser(
        "prod-a",
        help="产 A 总库（飞书 Bitable 在线只读）",
    )
    prod_a_sub = prod_a.add_subparsers(dest="prod_a_command")
    prod_a_check = prod_a_sub.add_parser(
        "check",
        help="试拉产 A 表并打印统计（不写本地文件）",
    )
    prod_a_check.add_argument("--config", default=None, help="feishu 配置路径")

    theme = sub.add_parser(
        "sync-theme",
        help="主题库（飞书 Bitable 在线只读）",
    )
    theme_sub = theme.add_subparsers(dest="theme_command")
    theme_check = theme_sub.add_parser(
        "check",
        help="试拉三张主题库表并打印统计（不写本地文件）",
    )
    theme_check.add_argument("--config", default=None, help="feishu 配置路径")
    theme_list = theme_sub.add_parser(
        "list-available",
        help="列出可用主题（使用人为空，状态为空或待使用）",
    )
    theme_list.add_argument("--config", default=None, help="feishu 配置路径")
    theme_list.add_argument("--limit", type=int, default=20, help="最多打印条数")

    args = parser.parse_args(argv)
    if args.command == "check-env":
        config_path = Path(args.config).expanduser() if args.config else None
        config = load_feishu_config(config_path)
        return 0 if run_check(config) else 1

    if args.command == "prod-a" and args.prod_a_command == "check":
        config_path = Path(args.config).expanduser() if args.config else None
        config = load_feishu_config(config_path)
        try:
            result = probe_prod_a_registry(config)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1
        print(f">>> 产 A 在线拉取 OK: {result['source']}")
        print(
            f"    table={result['table_id']} · {result['entries']} 条 · "
            f"{result['summary']}"
        )
        return 0

    if args.command == "sync-theme" and args.theme_command == "check":
        config_path = Path(args.config).expanduser() if args.config else None
        config = load_feishu_config(config_path)
        try:
            result = probe_theme_library_index(config)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1
        print(
            f">>> 主题库在线拉取 OK: 已绑定 {result['assigned_entries']} · "
            f"可用 {result['available_entries']}"
        )
        print(f"    tables={', '.join(result['tables'])}")
        if result["sample_apps"]:
            print(f"    sample_apps={', '.join(result['sample_apps'])}")
        if result.get("sample_available_codes"):
            print(f"    sample_available={', '.join(result['sample_available_codes'])}")
        return 0

    if args.command == "sync-theme" and args.theme_command == "list-available":
        config_path = Path(args.config).expanduser() if args.config else None
        config = load_feishu_config(config_path)
        try:
            index = fetch_available_theme_index(config)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1
        limit = max(1, args.limit)
        print(f">>> 可用主题 {len(index)} 条（使用人为空，状态为空或待使用）")
        for code in sorted(index.keys())[:limit]:
            entry = index[code]
            cn = entry.get("theme_cn", "")
            track = entry.get("track", "")
            print(f"    {code}  {cn[:40]}  [{track}]")
        if len(index) > limit:
            print(f"    ... 共 {len(index)} 条，使用 --limit 查看更多")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
