"""CLI: parse one-line theme briefs into task.csv columns."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from batch.csv_tasks import load_task_csv_raw, write_task_csv_rows
from batch.task_schema import (
    COL_AUDIENCE,
    COL_CORE_SCENE,
    COL_LOCAL_FEATURE,
    COL_THEME_CN,
    COL_TRACK,
)
from batch.theme_audit import (
    audit_theme_brief,
    format_theme_audit_failure,
    parse_one_liner,
)


def apply_parsed_to_row(raw: dict[str, str], parsed: dict[str, str], *, overwrite: bool) -> None:
    for col in (COL_THEME_CN, COL_TRACK, COL_AUDIENCE, COL_CORE_SCENE, COL_LOCAL_FEATURE):
        val = parsed.get(col, "").strip()
        if not val:
            continue
        if overwrite or not str(raw.get(col) or "").strip():
            raw[col] = val


def compose_theme_to_csv(
    csv_path: Path,
    *,
    row: int,
    text: str,
    check_only: bool = False,
    overwrite: bool = True,
) -> tuple[bool, str]:
    """Parse text and optionally write theme columns for one CSV row."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"task.csv 不存在: {csv_path}")
    if row < 1:
        raise ValueError("row 须 ≥ 1")

    parsed = parse_one_liner(text)
    if not parsed.get(COL_THEME_CN):
        return False, "无法解析：请使用「产品名：机制描述…」格式"

    meta, rows_raw, fieldnames = load_task_csv_raw(csv_path)
    if row > len(rows_raw):
        raise ValueError(f"行号 {row} 超出范围（1-{len(rows_raw)}）")

    target = rows_raw[row - 1]
    row_name = (target.get("应用主名称") or "").strip() or f"行{row}"
    apply_parsed_to_row(target, parsed, overwrite=overwrite)

    audit = audit_theme_brief(
        theme_cn=target.get(COL_THEME_CN, ""),
        track=target.get(COL_TRACK, ""),
        audience=target.get(COL_AUDIENCE, ""),
        core_scene=target.get(COL_CORE_SCENE, ""),
        local_feature=target.get(COL_LOCAL_FEATURE, ""),
        product_flow=target.get("productFlow", ""),
        row_name=row_name,
    )

    if check_only:
        if audit.ok:
            return True, _format_success(row, row_name, audit.parsed, audit.suggest_topology)
        return False, format_theme_audit_failure(row, row_name, audit, csv_path=str(csv_path))

    if not audit.ok:
        return False, format_theme_audit_failure(row, row_name, audit, csv_path=str(csv_path))

    write_task_csv_rows(csv_path, meta, rows_raw, fieldnames=fieldnames)
    return True, _format_success(row, row_name, audit.parsed, audit.suggest_topology, saved=True)


def _format_success(
    row: int,
    row_name: str,
    parsed: dict[str, str],
    topology: list[str],
    *,
    saved: bool = False,
) -> str:
    lines = [
        f">>> compose-theme {'已写入' if saved else '校验通过'}: 行 {row} — {row_name}",
        "",
        "解析结果:",
    ]
    for col, label in (
        (COL_THEME_CN, "中文主题"),
        (COL_TRACK, "赛道分类"),
        (COL_AUDIENCE, "目标人群"),
        (COL_CORE_SCENE, "核心场景"),
        (COL_LOCAL_FEATURE, "本地功能"),
    ):
        lines.append(f"  {label}: {parsed.get(col, '')}")
    if topology:
        lines.append(f"  推荐 topology: {', '.join(topology[:3])}")
    if saved:
        lines.append("")
        lines.append("下一步: ./run.sh task-fill --force && ./run.sh task-ready")
    return "\n".join(lines)


def cmd_compose_theme(args: Namespace, cfg) -> int:
    csv_path = (args.csv or cfg.task_csv).resolve()
    texts: list[str] = []

    if args.text:
        texts.append(args.text.strip())
    if args.file:
        texts.extend(
            line.strip()
            for line in Path(args.file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    if not texts:
        print("错误: 请提供 --text 或 --file", file=sys.stderr)
        return 1

    row = int(args.row)
    ok_all = True
    for i, text in enumerate(texts):
        target_row = row + i
        try:
            ok, msg = compose_theme_to_csv(
                csv_path,
                row=target_row,
                text=text,
                check_only=args.check,
                overwrite=not args.no_overwrite,
            )
        except (OSError, ValueError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1
        print(msg)
        print("")
        ok_all = ok_all and ok
    return 0 if ok_all else 1
