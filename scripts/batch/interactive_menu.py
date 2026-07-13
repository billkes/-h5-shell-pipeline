"""Interactive main menu for h5-shell-pipeline: batch prep + production."""

from __future__ import annotations

import sys
from argparse import Namespace

from batch.config import BatchConfig
from batch.csv_tasks import load_task_csv_meta, load_tasks_for_run
from batch.task_cli import (
    cmd_add,
    cmd_audit,
    cmd_compose_theme,
    cmd_fill,
    cmd_init,
    cmd_list,
    cmd_ready,
    cmd_validate,
)


def _require_tty() -> bool:
    if sys.stdin.isatty():
        return True
    print("错误: 需要交互式终端，请直接运行 ./run.sh")
    return False


def _pause() -> None:
    input("\n按回车继续...")


def _input_yes_no(prompt: str, *, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} [{hint}]: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes", "是", "1"):
            return True
        if raw in ("n", "no", "否", "0"):
            return False
        print("  请输入 y 或 n")


def _input_int(prompt: str, *, default: int | None = None, minimum: int = 1) -> int:
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        if raw.isdigit():
            val = int(raw)
            if val >= minimum:
                return val
        print(f"  请输入 ≥{minimum} 的整数")


def _print_banner(title: str = "h5-shell-pipeline") -> None:
    print("")
    print("═" * 56)
    print(f"  {title}")
    print("═" * 56)


def _print_task_csv_summary(cfg: BatchConfig) -> None:
    path = cfg.task_csv.resolve()
    if not path.is_file():
        print("  任务台账: （尚未创建 task.csv）")
        return
    try:
        meta = load_task_csv_meta(path)
        default_type = cfg.batch_pack_type or "h5_swift_shell"
        tasks, rows = load_tasks_for_run(
            path,
            default_type,
            project_dir=cfg.project_dir,
        )
        batch_id = meta.batch_id or "—"
        print(f"  任务台账: {path.name} · batchId={batch_id}")
        print(f"  数据行: {len(rows)} · 可产包: {len(tasks)}")
    except (OSError, ValueError) as exc:
        print(f"  任务台账: {path.name}（读取异常: {exc}）")


def _ns(**kwargs: object) -> Namespace:
    return Namespace(csv=None, **kwargs)


def _prep_init(cfg: BatchConfig) -> int:
    print("\n── 初始化空 task.csv")
    path = cfg.task_csv.resolve()
    force = False
    if path.is_file():
        print(f"  已存在: {path}")
        if not _input_yes_no("覆盖重建?", default=False):
            return 0
        force = True
    batch_id = input("batchId（如 88-0714）: ").strip()
    if not batch_id:
        print("错误: batchId 不能为空")
        return 1
    rows = _input_int("空行数", default=1, minimum=1)
    return cmd_init(_ns(batch_id=batch_id, rows=rows, force=force), cfg)


def _prep_add(cfg: BatchConfig) -> int:
    print("\n── 追加空行")
    if not cfg.task_csv.is_file():
        print("错误: 请先初始化 task.csv")
        return 1
    count = _input_int("追加行数", minimum=1)
    return cmd_add(_ns(count=count), cfg)


def _prep_fill(cfg: BatchConfig) -> int:
    print("\n── 抽 Bridge 七维 + productFlow")
    if not cfg.task_csv.is_file():
        print("错误: task.csv 不存在")
        return 1
    force = _input_yes_no("强制重抽已有 Bridge 维度?", default=False)
    return cmd_fill(_ns(batch_id="", force=force), cfg)


def _prep_audit(cfg: BatchConfig) -> int:
    print("\n── 批内审计")
    if not cfg.task_csv.is_file():
        print("错误: task.csv 不存在")
        return 1
    return cmd_audit(_ns(), cfg)


def _prep_ready(cfg: BatchConfig) -> int:
    print("\n── 产包前验签")
    if not cfg.task_csv.is_file():
        print("错误: task.csv 不存在")
        return 1
    return cmd_ready(_ns(), cfg)


def _prep_validate(cfg: BatchConfig) -> int:
    print("\n── 基础格式校验")
    if not cfg.task_csv.is_file():
        print("错误: task.csv 不存在")
        return 1
    return cmd_validate(_ns(), cfg)


def _prep_list(cfg: BatchConfig) -> int:
    return cmd_list(_ns(), cfg)


def _prep_compose_theme(cfg: BatchConfig) -> int:
    if not cfg.task_csv.is_file():
        print("错误: task.csv 不存在")
        return 1
    row = _input_int("行号", minimum=1)
    print("粘贴一句话主题（回车结束）:")
    text = input().strip()
    if not text:
        print("错误: 内容为空")
        return 1
    return cmd_compose_theme(_ns(row=row, text=text, file=None, check=False, no_overwrite=False), cfg)


def _prep_standard_chain(cfg: BatchConfig) -> int:
    print("\n── 标准准备链：compose-theme → fill → audit → ready")
    if not cfg.task_csv.is_file():
        print("错误: task.csv 不存在")
        return 1
    steps: list[tuple[str, int]] = []
    for label, fn in (
        ("抽卡填维", lambda: cmd_fill(_ns(batch_id="", force=False), cfg)),
        ("批内审计", lambda: cmd_audit(_ns(), cfg)),
        ("产包前验签", lambda: cmd_ready(_ns(), cfg)),
    ):
        code = fn()
        steps.append((label, code))
        if code != 0:
            print(f">>> 准备链在「{label}」停止")
            break
    print("\n准备链结果:")
    for label, rc in steps:
        mark = "✅" if rc == 0 else "❌"
        print(f"  {mark} {label}")
    return steps[-1][1] if steps else 1


def _prep_template_build(cfg: BatchConfig) -> int:
    print("\n── 模板构建（无 Agent，仅套 Swift 壳模板）")
    import os

    host = input("H5_PROD_HOST: ").strip() or os.environ.get("H5_PROD_HOST", "")
    team = input("APPLE_TEAM_ID: ").strip() or os.environ.get("APPLE_TEAM_ID", "")
    from batch.legacy_cli import cmd_build_all

    return cmd_build_all(_ns(batch_id="", h5_host=host, team_id=team))


def interactive_prep_menu(cfg: BatchConfig) -> None:
    actions: dict[str, tuple[str, object]] = {
        "1": ("初始化 (init)", _prep_init),
        "2": ("追加空行 (add)", _prep_add),
        "3": ("自拟主题 (compose-theme)", _prep_compose_theme),
        "4": ("抽卡填维 (fill)", _prep_fill),
        "5": ("批内审计 (audit)", _prep_audit),
        "6": ("产包前验签 (ready)", _prep_ready),
        "7": ("格式校验 (validate)", _prep_validate),
        "8": ("列出任务 (list)", _prep_list),
        "9": ("标准准备链", _prep_standard_chain),
        "10": ("模板构建 (build-all)", _prep_template_build),
    }
    while True:
        _print_banner("批次准备 · task.csv")
        _print_task_csv_summary(cfg)
        print("")
        for key, (label, _) in actions.items():
            print(f"  [{key}] {label}")
        print("  [0] 返回主菜单")
        print("")
        choice = input("请选择: ").strip()
        if choice in ("0", ""):
            return
        action = actions.get(choice)
        if action is None:
            print("无效输入")
            continue
        label, fn = action
        try:
            rc = fn(cfg)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"错误: {exc}")
            rc = 1
        if rc != 0:
            print(f">>> {label} 未成功 (exit {rc})")
        _pause()


def interactive_main() -> int:
    if not _require_tty():
        return 1

    from batch.cli import _interactive_batch_run

    cfg = BatchConfig.from_env()
    while True:
        _print_banner()
        _print_task_csv_summary(cfg)
        print("")
        print("  [1] 开始产包（Agent 流水线）")
        print("  [2] 批次准备（task.csv）")
        print("  [0] 退出")
        print("")
        choice = input("请选择: ").strip()
        if choice in ("0", "q", "quit", "exit"):
            print("再见。")
            return 0
        if choice == "1":
            rc = _interactive_batch_run(show_banner=False)
            if rc != 0:
                print(f">>> 产包结束，退出码 {rc}")
            _pause()
            continue
        if choice == "2":
            interactive_prep_menu(cfg)
            continue
        print("无效输入，请重新选择")
