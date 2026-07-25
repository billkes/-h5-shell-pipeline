"""Task ledger schema: root ``task.csv`` is the single source of truth."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import ceil
from pathlib import Path

# ── Legacy 10 columns ──────────────────────────────────────────────────────
COL_NAME = "应用主名称"
COL_FULL_NAME = "全称"
COL_STATE_MANAGEMENT = "状态管理"
COL_ARCHITECTURE = "架构模式"
COL_NAMING_RULE = "命名混淆规则"
COL_PRIVACY_STYLE = "协议风格"
COL_PRIVACY_FILE = "隐私文件"
COL_GIT_URL = "仓库地址"
COL_FIRST_PRODUCT_CODE = "首个商品Code"
COL_PROGRAMMING_STYLE = "编程风格"

# ── Extended columns (task prep phase) ─────────────────────────────────────
COL_PACK_TYPE = "应用类型"
COL_THEME_CODE = "主题编号"
COL_THEME_CN = "中文主题"
COL_TRACK = "赛道分类"
COL_AUDIENCE = "目标人群"
COL_CORE_SCENE = "核心场景"
COL_LOCAL_FEATURE = "本地功能"
COL_PRODUCT_FLOW = "productFlow"

# ── H5 shell Bridge deck (7 dimensions) ───────────────────────────────────
COL_WEBVIEW_ENGINE = "webviewEngine"
COL_BRIDGE_CALL_STYLE = "bridgeCallStyle"
COL_BRIDGE_CALLBACK_STYLE = "bridgeCallbackStyle"
COL_BRIDGE_ENVELOPE = "bridgeEnvelope"
COL_MEDIA_SERVE = "mediaServe"
COL_BRIDGE_ERROR_CODE = "bridgeErrorCode"
COL_BRIDGE_INJECT_TIMING = "bridgeInjectTiming"

H5_SHELL_BRIDGE_DIM_TO_CSV: dict[str, str] = {
    "webviewEngine": COL_WEBVIEW_ENGINE,
    "bridgeCallStyle": COL_BRIDGE_CALL_STYLE,
    "bridgeCallbackStyle": COL_BRIDGE_CALLBACK_STYLE,
    "bridgeEnvelope": COL_BRIDGE_ENVELOPE,
    "mediaServe": COL_MEDIA_SERVE,
    "bridgeErrorCode": COL_BRIDGE_ERROR_CODE,
    "bridgeInjectTiming": COL_BRIDGE_INJECT_TIMING,
}

H5_SHELL_BRIDGE_PICK_ORDER: tuple[str, ...] = tuple(H5_SHELL_BRIDGE_DIM_TO_CSV.keys())

H5_SHELL_BRIDGE_COLUMNS: tuple[str, ...] = tuple(H5_SHELL_BRIDGE_DIM_TO_CSV.values())

# ── H5 kit deck (8 dimensions) ────────────────────────────────────────────
COL_KIT_ATOM_SET = "kitAtomSet"
COL_KIT_CSS_METHODOLOGY = "kitCssMethodology"
COL_KIT_ATOM_GRANULARITY = "kitAtomGranularity"
COL_KIT_DOM_SHAPE = "kitDomShape"
COL_KIT_JS_PATTERN = "kitJsPattern"
COL_KIT_JS_NAMESPACE = "kitJsNamespace"
COL_KIT_STORAGE_ADAPTER = "kitStorageAdapter"
COL_KIT_MOTION_APPROACH = "kitMotionApproach"
COL_H5_STATE_MODEL = "h5StateModel"
COL_H5_ROUTER_PATTERN = "h5RouterPattern"
COL_H5_SCREEN_PATTERN = "h5ScreenPattern"

# ── Per-row runtime flags (not deck-drawn) ────────────────────────────────
COL_REAL_ASSETS = "真图"

H5_KIT_DIM_TO_CSV: dict[str, str] = {
    "kitAtomSet": COL_KIT_ATOM_SET,
    "kitCssMethodology": COL_KIT_CSS_METHODOLOGY,
    "kitAtomGranularity": COL_KIT_ATOM_GRANULARITY,
    "kitDomShape": COL_KIT_DOM_SHAPE,
    "kitJsPattern": COL_KIT_JS_PATTERN,
    "kitJsNamespace": COL_KIT_JS_NAMESPACE,
    "kitStorageAdapter": COL_KIT_STORAGE_ADAPTER,
    "kitMotionApproach": COL_KIT_MOTION_APPROACH,
    "h5StateModel": COL_H5_STATE_MODEL,
    "h5RouterPattern": COL_H5_ROUTER_PATTERN,
    "h5ScreenPattern": COL_H5_SCREEN_PATTERN,
}

H5_KIT_PICK_ORDER: tuple[str, ...] = tuple(H5_KIT_DIM_TO_CSV.keys())

H5_KIT_COLUMNS: tuple[str, ...] = tuple(H5_KIT_DIM_TO_CSV.values())

LEGACY_COLUMNS: tuple[str, ...] = (
    COL_NAME,
    COL_FULL_NAME,
    COL_STATE_MANAGEMENT,
    COL_ARCHITECTURE,
    COL_NAMING_RULE,
    COL_PRIVACY_STYLE,
    COL_PRIVACY_FILE,
    COL_GIT_URL,
    COL_FIRST_PRODUCT_CODE,
    COL_PROGRAMMING_STYLE,
)

THEME_LIBRARY_COLUMNS: tuple[str, ...] = (
    COL_THEME_CODE,
    COL_THEME_CN,
    COL_TRACK,
    COL_AUDIENCE,
    COL_CORE_SCENE,
    COL_LOCAL_FEATURE,
    COL_PRODUCT_FLOW,
)

EXTENDED_COLUMNS: tuple[str, ...] = (
    COL_PACK_TYPE,
    *THEME_LIBRARY_COLUMNS,
)

H5_SHELL_EXTENDED_SUFFIX: tuple[str, ...] = H5_SHELL_BRIDGE_COLUMNS + H5_KIT_COLUMNS

# Row-level flags appended after Kit / topology columns
RUNTIME_FLAG_COLUMNS: tuple[str, ...] = (COL_REAL_ASSETS,)

STANDARD_COLUMNS: tuple[str, ...] = (
    LEGACY_COLUMNS + EXTENDED_COLUMNS + H5_SHELL_EXTENDED_SUFFIX + RUNTIME_FLAG_COLUMNS
)

BATCH_ID_COMMENT_RE = re.compile(r"^\s*#\s*batchId\s*:\s*(\S+)\s*$", re.IGNORECASE)

TASK_CSV_FILENAME = "task.csv"
DEFAULT_COOLDOWN_DAYS = 60


@dataclass(frozen=True)
class TaskCsvMeta:
    batch_id: str
    comment_lines: tuple[str, ...]


def task_csv_path(project_dir: Path) -> Path:
    return project_dir / TASK_CSV_FILENAME


def reports_dir(output_dir: Path) -> Path:
    return output_dir / "_reports"


def diversity_cap(n: int, k: int) -> int:
    """Max occurrences per value when spreading N items over K choices."""
    if n <= 0 or k <= 0:
        return 0
    return 1 if n <= k else ceil(n / k)


def parse_task_csv_meta(text: str) -> TaskCsvMeta:
    batch_id = ""
    comments: list[str] = []
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        comments.append(line)
        m = BATCH_ID_COMMENT_RE.match(line)
        if m:
            batch_id = m.group(1).strip().split(",")[0]
    return TaskCsvMeta(batch_id=batch_id, comment_lines=tuple(comments))


def format_task_csv_header(*, batch_id: str, extra_comments: tuple[str, ...] = ()) -> str:
    lines = [
        "# h5-shell-pipeline task ledger — single source of truth for the current run",
        f"# batchId: {batch_id}",
        "# 真图: 1=跑 agent.assets 换真图；0/空=仅占位（默认）",
    ]
    lines.extend(extra_comments)
    lines.append(",".join(STANDARD_COLUMNS))
    return "\n".join(lines) + "\n"


def parse_real_assets_flag(raw: str | None) -> bool:
    """Parse task.csv「真图」cell. Empty / 0 → False; 1/true/yes → True."""
    text = (raw or "").strip().lower()
    if not text:
        return False
    if text in ("1", "true", "yes", "y", "on"):
        return True
    if text in ("0", "false", "no", "n", "off"):
        return False
    raise ValueError(f"真图列取值无效: {raw!r}（允许 0/1、true/false、yes/no，空=0）")
