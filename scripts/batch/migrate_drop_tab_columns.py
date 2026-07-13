#!/usr/bin/env python3
"""One-off: remove legacy tab1Name/tab2Name/tab3Name columns from task.csv."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from batch.config import _project_root
from batch.csv_tasks import write_task_csv_rows
from batch.task_schema import STANDARD_COLUMNS, parse_task_csv_meta, task_csv_path

_LEGACY_TAB_COLUMNS = ("tab1Name", "tab2Name", "tab3Name")


def migrate_task_csv(path: Path) -> int:
    text = path.read_text(encoding="utf-8-sig")
    meta = parse_task_csv_meta(text)
    data_lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not data_lines:
        raise ValueError(f"task.csv 无数据: {path}")

    reader = csv.DictReader(data_lines)
    old_fields = list(reader.fieldnames or [])
    rows: list[dict[str, str]] = []

    for raw in reader:
        row = {c: (raw.get(c) or "").strip() for c in old_fields}
        for col in _LEGACY_TAB_COLUMNS:
            row.pop(col, None)
        out = {c: row.get(c, "") for c in STANDARD_COLUMNS}
        rows.append(out)

    write_task_csv_rows(path, meta, rows)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    _ = argv
    root = _project_root()
    path = task_csv_path(root)
    if not path.is_file():
        print(f"错误: 不存在 {path}", file=sys.stderr)
        return 1
    n = migrate_task_csv(path)
    print(f">>> 已移除 tab1/2/3Name 列，迁移 {n} 行: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
