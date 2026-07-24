"""Per-package dimension lock file — single source of truth after Phase 0."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from batch.architecture_folders import generate_architecture_folders
from batch.csv_architecture import COMBO_FILE, parse_architecture_from_csv
from batch.csv_tasks import (
    CsvTaskRow,
    COL_ARCHITECTURE,
    COL_NAMING_RULE,
    COL_PROGRAMMING_STYLE,
    COL_STATE_MANAGEMENT,
    is_allowed_state_pattern,
    normalize_architecture_pattern,
    normalize_naming_obfuscation_rule,
    normalize_programming_style,
    normalize_state_management,
)
from batch.config import BatchConfig
from batch.dimension_ledger import (
    ledger_path,
    validate_ledger,
)
from batch.pack_type import is_h5_shell
from batch.programming_layout import enrich_programming_style_block

LOCK_FILE = "本包维度锁.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_combo(workspace: Path) -> dict[str, Any]:
    combo = workspace / COMBO_FILE
    if not combo.is_file():
        return {}
    try:
        data = json.loads(combo.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def build_lock_payload(
    workspace: Path,
    row: CsvTaskRow,
    *,
    dart_package_name: str = "",
    batch_id: str = "",
) -> dict[str, Any]:
    """Build lock JSON from CSV row + merged combo file."""
    spec = parse_architecture_from_csv(row.state_management, row.architecture_pattern)
    combo = _read_combo(workspace)
    prefix = str(combo.get("dartCodePrefix") or "").strip()
    from batch.csv_naming import ensure_naming_rule_meta_v2

    meta = combo.get("namingRuleMeta")
    if not isinstance(meta, dict):
        meta = {}
    meta = ensure_naming_rule_meta_v2(
        meta,
        package_seed=prefix,
        rule_label=row.naming_obfuscation_rule,
        batch_id=batch_id,
    )

    folders = combo.get("architectureFolders")
    if not isinstance(folders, dict) or not folders:
        if prefix:
            folders = generate_architecture_folders(
                prefix=prefix,
                pattern_key=spec.architecture_pattern,
                workspace=workspace,
                app_name=row.name,
                naming_rule_label=row.naming_obfuscation_rule,
            )
        else:
            folders = {}

    return {
        "lockedAt": _utc_now(),
        "batchId": batch_id,
        "dartPackageName": dart_package_name,
        "stateManagement": {
            "key": spec.state_management,
            "label": spec.state_label,
            "enforcement": "hard",
        },
        "architecturePattern": {
            "key": spec.architecture_pattern,
            "label": spec.pattern_label,
            "enforcement": "hard",
        },
        "architectureFolders": folders,
        "namingObfuscationRule": {
            "value": row.naming_obfuscation_rule,
            "dartCodePrefix": prefix,
            "namingRuleMeta": meta,
            "enforcement": "hard",
        },
        "programmingStyle": enrich_programming_style_block(
            {
                "value": row.programming_style,
                "enforcement": "soft",
            },
            persona=row.programming_style,
            prefix=prefix,
            lock={
                "namingObfuscationRule": {
                    "dartCodePrefix": prefix,
                    "namingRuleMeta": meta,
                },
            },
            include_h5_vault=is_h5_shell(getattr(row, "pack_type", "") or ""),
            app_name=str(getattr(row, "name", "") or ""),
        ),
        "scaffoldFiles": combo.get("scaffoldFiles") or [],
    }


def write_dimension_lock(
    workspace: Path,
    row: CsvTaskRow,
    *,
    dart_package_name: str = "",
    batch_id: str = "",
) -> Path:
    """Write 本包维度锁.json after combo merge."""
    payload = build_lock_payload(
        workspace,
        row,
        dart_package_name=dart_package_name,
        batch_id=batch_id,
    )
    combo = _read_combo(workspace)
    if combo and payload.get("architectureFolders") and not combo.get("architectureFolders"):
        combo["architectureFolders"] = payload["architectureFolders"]
        (workspace / COMBO_FILE).write_text(
            json.dumps(combo, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    path = workspace / LOCK_FILE
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def ensure_code_dimensions_locked(
    cfg: BatchConfig,
    workspace: Path,
    row: CsvTaskRow,
    *,
    dart_package_name: str = "",
    batch_id: str = "",
) -> Path:
    """Alloc code combo + write 本包维度锁.json once, before skill.adapt (dartCodePrefix)."""
    from batch.workspace import alloc_code_combo

    lock_path = workspace / LOCK_FILE
    combo_path = workspace / COMBO_FILE
    if lock_path.is_file() and combo_path.is_file():
        return lock_path
    alloc_code_combo(cfg, workspace)
    return write_dimension_lock(
        workspace,
        row,
        dart_package_name=dart_package_name,
        batch_id=batch_id,
    )


def read_dimension_lock(workspace: Path) -> dict[str, Any] | None:
    """Read lock file; return None if missing."""
    path = workspace / LOCK_FILE
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def locked_code_prefix(workspace: Path) -> str:
    """Authoritative dartCodePrefix from early dimension lock."""
    lock = read_dimension_lock(workspace)
    if not lock:
        return ""
    naming = lock.get("namingObfuscationRule") or {}
    return str(naming.get("dartCodePrefix") or "").strip()


def locked_architecture_folders(workspace: Path) -> dict[str, dict[str, str]] | None:
    lock = read_dimension_lock(workspace)
    if not lock:
        return None
    folders = lock.get("architectureFolders")
    if not isinstance(folders, dict) or not folders:
        return None
    return folders  # type: ignore[return-value]


def lock_from_combo_fallback(workspace: Path) -> dict[str, Any] | None:
    """Fallback for legacy workspaces without lock file."""
    combo = _read_combo(workspace)
    if not combo:
        return None
    state_key = str(combo.get("stateManagement") or "").strip()
    pattern_key = str(combo.get("architecturePattern") or "").strip()
    if not state_key or not pattern_key:
        return None
    return {
        "lockedAt": "",
        "batchId": "",
        "dartPackageName": "",
        "stateManagement": {
            "key": state_key,
            "label": str(combo.get("csvStateManagement") or state_key),
            "enforcement": "hard",
        },
        "architecturePattern": {
            "key": pattern_key,
            "label": str(combo.get("csvArchitecturePattern") or pattern_key),
            "enforcement": "hard",
        },
        "architectureFolders": combo.get("architectureFolders") or {},
        "namingObfuscationRule": {
            "value": str(combo.get("namingObfuscationRule") or ""),
            "dartCodePrefix": str(combo.get("dartCodePrefix") or ""),
            "namingRuleMeta": combo.get("namingRuleMeta") or {},
            "enforcement": "hard",
        },
        "programmingStyle": {
            "value": str(combo.get("programmingStyle") or ""),
            "enforcement": "soft",
        },
        "scaffoldFiles": combo.get("scaffoldFiles") or [],
    }


def resolve_dimension_lock(workspace: Path) -> dict[str, Any] | None:
    """Prefer lock file; fall back to combo for legacy workspaces."""
    return read_dimension_lock(workspace) or lock_from_combo_fallback(workspace)


def update_scaffold_files(workspace: Path, files: list[str]) -> None:
    """Persist scaffold manifest into lock + combo."""
    lock = read_dimension_lock(workspace)
    if lock is not None:
        lock["scaffoldFiles"] = files
        (workspace / LOCK_FILE).write_text(
            json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    combo_path = workspace / COMBO_FILE
    if combo_path.is_file():
        try:
            combo = json.loads(combo_path.read_text(encoding="utf-8"))
            if isinstance(combo, dict):
                combo["scaffoldFiles"] = files
                combo_path.write_text(
                    json.dumps(combo, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        except json.JSONDecodeError:
            pass


def _validate_csv_row_dimensions(row: CsvTaskRow, line_hint: str) -> list[str]:
    errors: list[str] = []
    state = normalize_state_management(row.state_management)
    pattern = normalize_architecture_pattern(row.architecture_pattern)
    naming = normalize_naming_obfuscation_rule(row.naming_obfuscation_rule)
    style = normalize_programming_style(row.programming_style)

    for col, val in (
        (COL_STATE_MANAGEMENT, state),
        (COL_ARCHITECTURE, pattern),
        (COL_NAMING_RULE, naming),
        (COL_PROGRAMMING_STYLE, style),
    ):
        if not val:
            errors.append(f"{line_hint} {col} 为空或无效")

    if state and pattern:
        if not is_allowed_state_pattern(state, pattern):
            errors.append(
                f"{line_hint} 状态管理「{state}」与架构模式「{pattern}」"
                "不是合法配对"
            )
    return errors


def validate_batch_dimensions(cfg: BatchConfig) -> None:
    """Raise ValueError if batch CSV dimensions are incomplete or invalid."""
    if not cfg.task_csv_by_name:
        raise ValueError("批次 CSV 未加载")

    errors: list[str] = []
    seen_tokens: set[str] = set()

    for name, row in sorted(cfg.task_csv_by_name.items()):
        if not isinstance(row, CsvTaskRow):
            errors.append(f"任务 {name!r} 无有效 CSV 行")
            continue
        hint = f"应用「{name}」"
        errors.extend(_validate_csv_row_dimensions(row, hint))
        token = (
            f"{row.state_management}|{row.architecture_pattern}|"
            f"{row.naming_obfuscation_rule}|{row.programming_style}"
        )
        if token in seen_tokens:
            errors.append(f"{hint} 四维组合与批次内其它包重复: {token}")
        seen_tokens.add(token)

    ledger = ledger_path(cfg.project_dir)
    if ledger.is_file():
        ledger_errors = validate_ledger(ledger)
        errors.extend(f"账本: {e}" for e in ledger_errors)

    if errors:
        raise ValueError(
            "批次四维校验失败:\n" + "\n".join(f"  - {e}" for e in errors)
        )
