#!/usr/bin/env python3
"""Interactive menu for h5-shell-pipeline batch task CLI.

Replaces the previous shell-based menu (run.bat/run.ps1/run.sh) with a single
cross-platform Python implementation. Key feature: build/task-show list all
tasks first and let the user pick by index or name (like cursor-ios-batch).
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


def _print_menu() -> None:
    print()
    print("h5-shell-pipeline task CLI")
    print()
    print("请选择操作：")
    print("  1. task-list       列出所有任务")
    print("  2. task-validate   校验 task.csv")
    print("  3. task-ready      产包前严格校验")
    print("  4. task-fill-flow  自动填充 productFlow")
    print("  5. task-show       查看单个任务")
    print("  6. build-all       构建全部任务")
    print("  7. build           构建单个任务")
    print("  0. 退出")
    print()


def _select_task(prompt: str = "请输入编号或应用名（q 返回）: ") -> str | None:
    """列出所有任务，让用户用编号或名称选择。

    Returns 选中的应用主名称，或 None 表示取消。
    """
    from batch.config import BatchConfig
    from batch.csv_tasks import load_task_csv_raw

    cfg = BatchConfig.from_env()
    try:
        _, raw_rows, _ = load_task_csv_raw(cfg.task_csv)
    except Exception as exc:
        print(f"❌ 读取失败: {exc}")
        return None
    if not raw_rows:
        print("（无任务）")
        return None
    print()
    print(f"{'#':<4} {'应用主名称':<16} {'应用类型':<16} {'编程风格':<10}")
    print("-" * 50)
    for idx, raw in enumerate(raw_rows, start=1):
        name = raw.get("应用主名称", "").strip() or "(空)"
        pack = raw.get("应用类型", "").strip() or "-"
        style = raw.get("编程风格", "").strip() or "-"
        print(f"{idx:<4} {name:<16} {pack:<16} {style:<10}")
    print()
    try:
        choice = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not choice or choice.lower() in ("q", "quit", "exit"):
        return None
    # 数字 → 按编号选
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(raw_rows):
            name = raw_rows[idx - 1].get("应用主名称", "").strip()
            if name:
                return name
            print("❌ 该行为空应用主名称")
            return None
        print(f"❌ 编号超出范围: {idx}")
        return None
    # 否则按名称匹配
    for raw in raw_rows:
        if raw.get("应用主名称", "").strip() == choice:
            return choice
    print(f"❌ 未找到任务: {choice}")
    return None


def _run(argv: list[str]) -> None:
    """通过 argv 调用 CLI 命令。"""
    from batch.__main__ import main

    try:
        main(argv)
    except SystemExit:
        pass
    except Exception as exc:
        print(f"❌ 执行失败: {exc}")


def _prompt(prompt: str) -> str | None:
    """安全读取一行输入，EOF/Ctrl+C 返回 None。"""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _menu_build_all() -> None:
    """交互式 build-all：提示输入 h5-host 和 team-id。"""
    host = _prompt("请输入 h5-host: ")
    if not host:
        print("❌ h5-host 不能为空")
        return
    team_id = _prompt("请输入 team-id: ")
    if not team_id:
        print("❌ team-id 不能为空")
        return
    _run(["build-all", "--h5-host", host, "--team-id", team_id])


def interactive_main() -> int:
    """交互式菜单主入口。"""
    while True:
        try:
            _print_menu()
            choice = input("请输入选项: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not choice:
            continue
        if choice in ("0", "q", "quit", "exit"):
            return 0
        if choice == "1":
            _run(["task-list"])
        elif choice == "2":
            _run(["task-validate"])
        elif choice == "3":
            _run(["task-ready"])
        elif choice == "4":
            _run(["task-fill-flow"])
        elif choice == "5":
            name = _select_task()
            if name:
                _run(["task-show", name])
        elif choice == "6":
            _menu_build_all()
        elif choice == "7":
            name = _select_task()
            if name:
                _run(["build", name])
        else:
            print(f"无效选项: {choice}")


if __name__ == "__main__":
    sys.exit(interactive_main())
