"""Theme library index — Feishu online (prep) or legacy CSV exports (tests/migrate)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from batch.pack_type import H5_FLUTTER_SHELL, H5_OC_SHELL, H5_SHELL, H5_SWIFT_SHELL

THEME_GLOB = "*主题库*.csv"

THEME_INDEX_ALIASES: dict[str, tuple[str, ...]] = {
    "app_name": ("应用名", "应用主名称"),
    "theme_code": ("编号",),
    "theme_cn": ("主题名称",),
    "track": ("赛道分类",),
    "audience": ("目标人群",),
    "core_scene": ("核心场景",),
    "local_feature": ("本地功能",),
    "pack_type_label": ("应用类型",),
}

# Backward-compatible alias for internal callers
_COL_ALIASES = THEME_INDEX_ALIASES

DEFAULT_THEME_USAGE_FIELDS: dict[str, str] = {
    "assignee": "使用人",
    "status": "使用状态",
}

# 主题库1/2 在线表「使用状态」列名与默认不同（见 feishu.yaml per-table usage_fields）
THEME_USAGE_STATUS_ALIASES: tuple[str, ...] = (
    "使用状态",
    "文本",
    "是否重复",
)

PACK_TYPE_LABEL_MAP: dict[str, str] = {
    "工具包": "tool_flutter",
    "tool_flutter": "tool_flutter",
    "contentpack": "contentpack",
    "videostream": "videostream",
    "H5壳": H5_SHELL,
    "H5壳-Flutter": H5_FLUTTER_SHELL,
    "H5壳-Swift": H5_SWIFT_SHELL,
    "H5壳-OC": H5_OC_SHELL,
    H5_SHELL: H5_SHELL,
    H5_FLUTTER_SHELL: H5_FLUTTER_SHELL,
    H5_SWIFT_SHELL: H5_SWIFT_SHELL,
    H5_OC_SHELL: H5_OC_SHELL,
}


def is_theme_row_available(
    record: dict[str, str],
    *,
    assignee_col: str = "使用人",
    status_col: str = "使用状态",
) -> bool:
    """True when 使用人 is empty and 使用状态 is empty or 待使用 — pickable for a new pack."""
    assignee = (record.get(assignee_col) or "").strip()
    status = (record.get(status_col) or "").strip()
    if assignee:
        return False
    return not status or status == "待使用"


def pack_type_from_theme_label(label: str) -> str:
    text = (label or "").strip()
    if not text:
        return ""
    if text in PACK_TYPE_LABEL_MAP:
        return PACK_TYPE_LABEL_MAP[text]
    return (
        text
        if text
        in {
            "tool",
            "tool_oc",
            "tool_flutter",
            "contentpack",
            "videostream",
            H5_SHELL,
            H5_FLUTTER_SHELL,
            H5_SWIFT_SHELL,
            H5_OC_SHELL,
        }
        else ""
    )


def _resolve_header(fieldnames: list[str] | None) -> dict[str, str]:
    if not fieldnames:
        return {}
    header_map: dict[str, str] = {}
    for canonical, aliases in THEME_INDEX_ALIASES.items():
        for alias in aliases:
            if alias in fieldnames:
                header_map[canonical] = alias
                break
    return header_map


def _cell(row: dict[str, str], header: str) -> str:
    return (row.get(header) or "").strip()


def theme_entry_from_record(
    record: dict[str, str],
    *,
    field_map: dict[str, str] | None = None,
    require_app_name: bool = True,
) -> dict[str, str]:
    """Build canonical theme index entry from a Bitable/CSV row."""
    fmap = field_map or {k: v[0] for k, v in THEME_INDEX_ALIASES.items() if v}
    app_col = fmap.get("app_name", "应用名")
    name = _cell(record, app_col)
    entry: dict[str, str] = {}
    if name:
        entry["app_name"] = name
    for key, col in fmap.items():
        if key == "app_name":
            continue
        val = _cell(record, col)
        if val:
            entry[key] = val
    if require_app_name and not name:
        return {}
    if not entry.get("theme_code") and not name:
        return {}
    return entry


def load_theme_library_index(search_dirs: list[Path]) -> dict[str, dict[str, str]]:
    """``{应用名: {theme_code, theme_cn, track, …}}`` — later files override."""
    index: dict[str, dict[str, str]] = {}
    for base in search_dirs:
        if not base.is_dir():
            continue
        for path in sorted(base.glob(THEME_GLOB)):
            if not path.is_file():
                continue
            with path.open(encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                headers = _resolve_header(list(reader.fieldnames or []))
                if "app_name" not in headers:
                    continue
                for raw in reader:
                    entry = theme_entry_from_record(raw, field_map=headers)
                    if not entry:
                        continue
                    app = entry.pop("app_name")
                    pack_label = entry.pop("pack_type_label", "")
                    if pack_label:
                        pack = pack_type_from_theme_label(pack_label)
                        if pack:
                            entry["pack_type"] = pack
                    if entry:
                        index[app] = entry
    return index


def load_online_theme_library_index(config: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    """Fetch theme index from Feishu Bitable (prep phase source of truth)."""
    from batch.feishu_config import load_feishu_config
    from batch.feishu_theme_sync import fetch_theme_library_index

    cfg = config or load_feishu_config()
    return fetch_theme_library_index(cfg)


def default_theme_library_dirs(project_dir: Path) -> list[Path]:
    """Legacy CSV exports only — prep must use ``load_online_theme_library_index``."""
    return [project_dir / "data" / "imports"]
