"""Sync task.csv theme + 产A columns from Feishu online tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from batch.csv_tasks import CsvTaskRow, load_csv_tasks, load_task_csv_raw, write_task_csv_rows
from batch.feishu_config import load_feishu_config
from batch.feishu_theme_sync import fetch_theme_library_index
from batch.feishu_prod_a import fetch_prod_a_entries
from batch.prod_a_registry import (
    ProdARegistry,
    build_prod_a_registry,
    validate_batch_against_registry,
)
from batch.task_schema import (
    COL_AUDIENCE,
    COL_CORE_SCENE,
    COL_FIRST_PRODUCT_CODE,
    COL_FULL_NAME,
    COL_LOCAL_FEATURE,
    COL_NAME,
    COL_PACK_TYPE,
    COL_THEME_CN,
    COL_THEME_CODE,
    COL_TRACK,
)

THEME_KEY_TO_CSV: dict[str, str] = {
    "theme_code": COL_THEME_CODE,
    "theme_cn": COL_THEME_CN,
    "track": COL_TRACK,
    "audience": COL_AUDIENCE,
    "core_scene": COL_CORE_SCENE,
    "local_feature": COL_LOCAL_FEATURE,
}

PROD_A_CSV_COLUMNS: tuple[tuple[str, str], ...] = (
    ("full_name", COL_FULL_NAME),
    ("first_product_code", COL_FIRST_PRODUCT_CODE),
)


@dataclass
class FeishuPrepSources:
    prod_registry: ProdARegistry
    theme_index: dict[str, dict[str, str]]


@dataclass
class SyncChange:
    app: str
    column: str
    old: str
    new: str


@dataclass
class SyncReport:
    updated_rows: int = 0
    changes: list[SyncChange] = field(default_factory=list)
    missing_theme: list[str] = field(default_factory=list)
    missing_prod_a: list[str] = field(default_factory=list)


def load_feishu_prep_sources(config_path: Path | None = None) -> FeishuPrepSources:
    config = load_feishu_config(config_path)
    prod_cfg = config.get("feishu", {}).get("prod_a_task") or {}
    table_id = str(prod_cfg.get("table_id") or "unknown")
    entries = fetch_prod_a_entries(config)
    registry = build_prod_a_registry(entries, source=f"feishu:{table_id}")
    theme_index = fetch_theme_library_index(config)
    return FeishuPrepSources(prod_registry=registry, theme_index=theme_index)


def _theme_row_attr(col: str) -> str:
    mapping = {
        COL_THEME_CODE: "theme_code",
        COL_THEME_CN: "theme_cn",
        COL_TRACK: "track",
        COL_AUDIENCE: "audience",
        COL_CORE_SCENE: "core_scene",
        COL_LOCAL_FEATURE: "local_feature",
        COL_PACK_TYPE: "pack_type",
        COL_FULL_NAME: "full_name",
        COL_FIRST_PRODUCT_CODE: "first_product_code",
    }
    return mapping[col]


def audit_feishu_alignment(
    rows: list[CsvTaskRow],
    sources: FeishuPrepSources,
) -> list[str]:
    """Strict check: task.csv must match online 产A + 主题库."""
    issues: list[str] = []
    issues.extend(validate_batch_against_registry(rows, sources.prod_registry))

    for row in rows:
        theme = sources.theme_index.get(row.name)
        if not theme:
            issues.append(f"「{row.name}」不在主题库在线表")
            continue
        for key, col in THEME_KEY_TO_CSV.items():
            online = (theme.get(key) or "").strip()
            attr = _theme_row_attr(col)
            csv_val = str(getattr(row, attr, "") or "").strip()
            if not online:
                continue
            if not csv_val:
                issues.append(f"「{row.name}」缺少 {col}（在线={online!r}）")
            elif csv_val != online:
                issues.append(
                    f"「{row.name}」{col} 与主题库不一致: "
                    f"CSV={csv_val!r} 在线={online!r}"
                )
        online_pack = (theme.get("pack_type") or "").strip()
        if online_pack and row.pack_type and row.pack_type != online_pack:
            issues.append(
                f"「{row.name}」应用类型与主题库不一致: "
                f"CSV={row.pack_type!r} 在线={online_pack!r}"
            )

        prod = sources.prod_registry.lookup(row.name)
        if not prod:
            issues.append(f"「{row.name}」不在产A在线总库")
            continue
        if row.full_name and prod.full_name and row.full_name != prod.full_name:
            issues.append(
                f"「{row.name}」全称与产A总库不一致: "
                f"CSV={row.full_name!r} 在线={prod.full_name!r}"
            )
        if (
            row.first_product_code
            and prod.first_product_code
            and row.first_product_code != prod.first_product_code
        ):
            issues.append(
                f"「{row.name}」首个商品Code与产A总库不一致: "
                f"CSV={row.first_product_code!r} 在线={prod.first_product_code!r}"
            )
    return issues


def _apply_row_sync(
    row: dict[str, str],
    *,
    sources: FeishuPrepSources,
    report: SyncReport,
    overwrite: bool,
) -> bool:
    app = (row.get(COL_NAME) or "").strip()
    if not app:
        return False

    changed = False
    theme = sources.theme_index.get(app)
    if theme:
        for key, col in THEME_KEY_TO_CSV.items():
            online = (theme.get(key) or "").strip()
            if not online:
                continue
            old = (row.get(col) or "").strip()
            if overwrite or not old:
                if old != online:
                    report.changes.append(SyncChange(app, col, old, online))
                    row[col] = online
                    changed = True
        online_pack = (theme.get("pack_type") or "").strip()
        if online_pack:
            old = (row.get(COL_PACK_TYPE) or "").strip()
            if overwrite or not old:
                if old != online_pack:
                    report.changes.append(
                        SyncChange(app, COL_PACK_TYPE, old, online_pack)
                    )
                    row[COL_PACK_TYPE] = online_pack
                    changed = True
    else:
        report.missing_theme.append(app)

    prod = sources.prod_registry.lookup(app)
    if prod:
        for attr, col in PROD_A_CSV_COLUMNS:
            online = getattr(prod, attr, "").strip()
            if not online:
                continue
            old = (row.get(col) or "").strip()
            if overwrite or not old:
                if old != online:
                    report.changes.append(SyncChange(app, col, old, online))
                    row[col] = online
                    changed = True
    else:
        report.missing_prod_a.append(app)

    return changed


def sync_task_csv_from_feishu(
    csv_path: Path,
    *,
    config_path: Path | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
    only_apps: set[str] | None = None,
) -> SyncReport:
    """Pull 产A + 主题库 columns into task.csv for rows with 应用主名称."""
    sources = load_feishu_prep_sources(config_path)
    meta, rows, fieldnames = load_task_csv_raw(csv_path)
    report = SyncReport()

    for row in rows:
        app = (row.get(COL_NAME) or "").strip()
        if not app:
            continue
        if only_apps is not None and app not in only_apps:
            continue
        if _apply_row_sync(row, sources=sources, report=report, overwrite=overwrite):
            report.updated_rows += 1

    if not dry_run and report.changes:
        write_task_csv_rows(csv_path, meta, rows, fieldnames)
    return report


def format_sync_report(report: SyncReport, *, dry_run: bool = False) -> str:
    lines: list[str] = []
    prefix = "将" if dry_run else "已"
    if report.changes:
        lines.append(f">>> {prefix}同步 {len(report.changes)} 处字段（{report.updated_rows} 行有变更）")
        for ch in report.changes[:30]:
            old = ch.old or "(空)"
            lines.append(f"    {ch.app} · {ch.column}: {old!r} → {ch.new!r}")
        if len(report.changes) > 30:
            lines.append(f"    ... 共 {len(report.changes)} 处")
    else:
        lines.append(">>> 无字段变更")

    if report.missing_theme:
        lines.append(f"警告: 主题库未找到: {', '.join(report.missing_theme)}")
    if report.missing_prod_a:
        lines.append(f"警告: 产A总库未找到: {', '.join(report.missing_prod_a)}")
    return "\n".join(lines)
