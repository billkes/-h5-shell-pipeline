"""Fetch theme libraries from Feishu Bitable (online only)."""

from __future__ import annotations

from typing import Any

from batch.feishu_bitable import fetch_bitable_records, rows_to_dicts
from batch.feishu_config import get_base_token, get_theme_libraries
from batch.theme_library import (
    DEFAULT_THEME_USAGE_FIELDS,
    THEME_INDEX_ALIASES,
    is_theme_row_available,
    pack_type_from_theme_label,
    theme_entry_from_record,
)


def _field_map(config: dict[str, Any]) -> dict[str, str]:
    """Logical key → Bitable column name."""
    defaults = {
        "app_name": "应用名",
        "theme_code": "编号",
        "theme_cn": "主题名称",
        "track": "赛道分类",
        "audience": "目标人群",
        "core_scene": "核心场景",
        "local_feature": "本地功能",
        "pack_type_label": "应用类型",
    }
    feishu = config.get("feishu") or {}
    overrides = feishu.get("theme_fields") or {}
    if not isinstance(overrides, dict):
        overrides = {}
    out = dict(defaults)
    for key, col in overrides.items():
        if col:
            out[str(key)] = str(col)
    return out


def _usage_field_map(config: dict[str, Any], lib_cfg: dict[str, Any]) -> dict[str, str]:
    """Resolve 使用人 / 使用状态 column names (per-table overrides)."""
    feishu = config.get("feishu") or {}
    global_usage = feishu.get("theme_usage_fields") or {}
    if not isinstance(global_usage, dict):
        global_usage = {}
    per_table = lib_cfg.get("usage_fields") or {}
    if not isinstance(per_table, dict):
        per_table = {}
    merged = dict(DEFAULT_THEME_USAGE_FIELDS)
    for key in ("assignee", "status"):
        if global_usage.get(key):
            merged[key] = str(global_usage[key])
        if per_table.get(key):
            merged[key] = str(per_table[key])
    return merged


def _table_field_map(lib_cfg: dict[str, Any], global_map: dict[str, str]) -> dict[str, str]:
    per_table = lib_cfg.get("fields")
    if not isinstance(per_table, dict):
        return global_map
    merged = dict(global_map)
    for key, col in per_table.items():
        if col:
            merged[str(key)] = str(col)
    return merged


def fetch_theme_records_from_table(
    *,
    base_token: str,
    table_id: str,
    field_map: dict[str, str],
    view_id: str = "",
) -> list[dict[str, str]]:
    field_names, rows = fetch_bitable_records(
        base_token=base_token,
        table_id=table_id,
        view_id=view_id,
    )
    records = rows_to_dicts(field_names, rows)
    app_col = field_map.get("app_name", "应用名")
    if app_col and app_col not in field_names:
        raise ValueError(f"Bitable {table_id} 缺少列: {app_col}")
    return records


def _entry_from_record(
    record: dict[str, str],
    *,
    field_map: dict[str, str],
    source: str,
    require_app_name: bool = True,
) -> dict[str, str]:
    entry = theme_entry_from_record(
        record,
        field_map=field_map,
        require_app_name=require_app_name,
    )
    if not entry:
        return {}
    app = entry.pop("app_name", "")
    pack_label = entry.pop("pack_type_label", "")
    if pack_label:
        pack = pack_type_from_theme_label(pack_label)
        if pack:
            entry["pack_type"] = pack
    if app:
        entry["_app_name"] = app
    entry["_source"] = source
    return entry


def build_theme_index(
    records: list[dict[str, str]],
    *,
    field_map: dict[str, str],
    source: str,
    usage_map: dict[str, str] | None = None,
    assigned_only: bool = True,
    available_only: bool = False,
) -> dict[str, dict[str, str]]:
    """Build theme index keyed by 应用名 (assigned) or 编号 (available pool).

    - ``assigned_only=True`` (default, for ``sync-feishu``): rows with 应用名,
      regardless of 使用状态/使用人 — already-bound themes like Petioo.
    - ``available_only=True`` (for picking new themes): 使用人 and 使用状态
      must both be empty; keyed by theme_code.
    """
    if assigned_only and available_only:
        raise ValueError("assigned_only 与 available_only 不能同时为 True")

    usage = usage_map or DEFAULT_THEME_USAGE_FIELDS
    assignee_col = usage.get("assignee") or "使用人"
    status_col = usage.get("status") or "使用状态"

    index: dict[str, dict[str, str]] = {}
    for record in records:
        if available_only and not is_theme_row_available(
            record,
            assignee_col=assignee_col,
            status_col=status_col,
        ):
            continue

        entry = _entry_from_record(
            record,
            field_map=field_map,
            source=source,
            require_app_name=assigned_only,
        )
        if not entry:
            continue

        app = entry.pop("_app_name", "")
        if assigned_only:
            if not app:
                continue
            key = app
        else:
            key = entry.get("theme_code") or entry.get("theme_cn") or app
            if not key:
                continue

        index[key] = entry
    return index


def _fetch_all_tables(
    config: dict[str, Any],
    *,
    assigned_only: bool,
    available_only: bool,
) -> dict[str, dict[str, str]]:
    base_token = get_base_token(config)
    libs = get_theme_libraries(config)
    if not libs:
        raise ValueError("feishu.yaml 缺少 feishu.theme_libraries")

    global_map = _field_map(config)
    index: dict[str, dict[str, str]] = {}

    for lib in libs:
        table_id = str(lib.get("table_id") or "").strip()
        if not table_id:
            continue
        view_id = str(lib.get("view_id") or "").strip()
        fmap = _table_field_map(lib, global_map)
        usage_map = _usage_field_map(config, lib)
        records = fetch_theme_records_from_table(
            base_token=base_token,
            table_id=table_id,
            field_map=fmap,
            view_id=view_id,
        )
        part = build_theme_index(
            records,
            field_map=fmap,
            source=f"feishu:{table_id}",
            usage_map=usage_map,
            assigned_only=assigned_only,
            available_only=available_only,
        )
        index.update(part)

    return index


def fetch_theme_library_index(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Assigned themes keyed by 应用名 — for ``task sync-feishu`` / audit."""
    index = _fetch_all_tables(config, assigned_only=True, available_only=False)
    if not index:
        raise RuntimeError("主题库 Bitable 无已绑定应用行（应用名为空）")
    return index


def fetch_available_theme_index(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Unused themes (使用人+使用状态均为空) keyed by 编号 — for new pack selection."""
    index = _fetch_all_tables(config, assigned_only=False, available_only=True)
    if not index:
        raise RuntimeError("主题库 Bitable 无可用行（使用人/使用状态均须为空）")
    return index


def probe_theme_library_index(config: dict[str, Any]) -> dict[str, Any]:
    """Fetch and summarize without writing any local file."""
    libs = get_theme_libraries(config)
    assigned = fetch_theme_library_index(config)
    try:
        available = fetch_available_theme_index(config)
        available_count = len(available)
    except RuntimeError:
        available_count = 0
        available = {}
    tables = [str(lib.get("table_id") or "") for lib in libs if lib.get("table_id")]
    sample_apps = sorted(assigned.keys())[:5]
    sample_codes = sorted(available.keys())[:5]
    return {
        "assigned_entries": len(assigned),
        "available_entries": available_count,
        "tables": tables,
        "sample_apps": sample_apps,
        "sample_available_codes": sample_codes,
        "aliases": list(THEME_INDEX_ALIASES.keys()),
    }
