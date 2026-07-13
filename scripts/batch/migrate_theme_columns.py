#!/usr/bin/env python3
"""One-off: flatten task.csv themeAngle → theme-library columns."""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

from batch.config import _project_root
from batch.csv_tasks import write_task_csv_rows
from batch.task_schema import (
    COL_AUDIENCE,
    COL_CORE_SCENE,
    COL_LOCAL_FEATURE,
    COL_NAME,
    COL_PRODUCT_FLOW,
    COL_THEME_CN,
    COL_THEME_CODE,
    COL_TRACK,
    STANDARD_COLUMNS,
    parse_task_csv_meta,
    task_csv_path,
)
from batch.theme_fields import parse_legacy_theme_angle
from batch.theme_library import default_theme_library_dirs, load_theme_library_index


def migrate_task_csv(path: Path, *, project_dir: Path) -> int:
    text = path.read_text(encoding="utf-8-sig")
    meta = parse_task_csv_meta(text)
    data_lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not data_lines:
        raise ValueError(f"task.csv 无数据: {path}")

    reader = csv.DictReader(data_lines)
    old_fields = list(reader.fieldnames or [])
    lib = load_theme_library_index(default_theme_library_dirs(project_dir))
    rows: list[dict[str, str]] = []

    for raw in reader:
        row = {c: (raw.get(c) or "").strip() for c in old_fields}
        name = row.get(COL_NAME, "")
        legacy = (row.pop("themeAngle", None) or row.get("themeAngle") or "").strip()
        parsed = parse_legacy_theme_angle(legacy) if legacy else {}
        entry = lib.get(name, {})

        out = {c: "" for c in STANDARD_COLUMNS}
        for col in old_fields:
            if col in STANDARD_COLUMNS and col != "themeAngle":
                out[col] = row.get(col, "")

        if entry.get("theme_code"):
            out[COL_THEME_CODE] = entry["theme_code"]
        if entry.get("theme_cn"):
            out[COL_THEME_CN] = entry["theme_cn"]
        for src, col in (
            ("track", COL_TRACK),
            ("audience", COL_AUDIENCE),
            ("core_scene", COL_CORE_SCENE),
            ("local_feature", COL_LOCAL_FEATURE),
        ):
            if entry.get(src):
                out[col] = entry[src]

        if parsed.get("product_flow"):
            out[COL_PRODUCT_FLOW] = parsed["product_flow"]
        for src, col in (
            ("track", COL_TRACK),
            ("audience", COL_AUDIENCE),
            ("core_scene", COL_CORE_SCENE),
            ("local_feature", COL_LOCAL_FEATURE),
        ):
            if not out[col] and parsed.get(src):
                out[col] = parsed[src]

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
    n = migrate_task_csv(path, project_dir=root)
    print(f">>> 已迁移 {n} 行 → 平铺主题库列: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
