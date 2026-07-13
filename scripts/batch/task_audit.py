"""Task ledger audits: batch diversity, deck combo ledger, soft single-dim balance."""

from __future__ import annotations

from collections import Counter
from math import ceil
from pathlib import Path

from batch.csv_tasks import CsvTaskRow, load_csv_tasks
from batch.pack_type import is_h5_shell
from batch.name_rules import audit_subtitle_a_face_diversity
from batch.registry import (
    audit_registry_duplicate_names,
    check_package_dict_similarity,
    ensure_contentpack_registry,
    load_registry_packages,
    registry_probe_from_task_row,
)
from batch.task_schema import (
    COL_ARCHITECTURE,
    COL_PROGRAMMING_STYLE,
    COL_STATE_MANAGEMENT,
    H5_SHELL_BRIDGE_COLUMNS,
    diversity_cap,
)


def _cap(n: int, k: int) -> int:
    return diversity_cap(n, k)


def audit_dimension_diversity(rows: list[CsvTaskRow]) -> list[str]:
    """Batch diversity for 状态管理 / 架构模式 (ios-03 §7.2)."""
    n = len(rows)
    if n == 0:
        return ["无数据行"]
    violations: list[str] = []
    checks = ((COL_STATE_MANAGEMENT, 6), (COL_ARCHITECTURE, 5))
    for col, k in checks:
        counts = Counter(getattr(r, _row_attr(col)) for r in rows)
        for val, cnt in counts.items():
            if not val:
                continue
            limit = _cap(n, k)
            if cnt > limit:
                violations.append(f"{col}「{val}」{cnt} 次 > 上限 {limit}")

    pair_counts = Counter(
        (r.state_management, r.architecture_pattern) for r in rows
    )
    pair_limit = _cap(n, 20)
    for pair, cnt in pair_counts.items():
        if cnt > pair_limit:
            violations.append(f"配对 {pair} {cnt} 次 > 上限 {pair_limit}")
    return violations


def _row_attr(col: str) -> str:
    mapping = {
        COL_STATE_MANAGEMENT: "state_management",
        COL_ARCHITECTURE: "architecture_pattern",
        COL_PROGRAMMING_STYLE: "programming_style",
    }
    return mapping[col]


def audit_h5_kit_filled(rows: list[CsvTaskRow]) -> list[str]:
    """Kit 八维暂未纳入 h5-shell-pipeline task.csv — 跳过校验。"""
    _ = rows
    return []


def audit_h5_shell_bridge_filled(rows: list[CsvTaskRow]) -> list[str]:
    """Ensure h5_shell rows have Bridge seven columns."""
    violations: list[str] = []
    h5_rows = [r for r in rows if is_h5_shell(r.pack_type)]
    if not h5_rows:
        return violations
    attr_map = {
        "webviewEngine": "webview_engine",
        "bridgeCallStyle": "bridge_call_style",
        "bridgeCallbackStyle": "bridge_callback_style",
        "bridgeEnvelope": "bridge_envelope",
        "mediaServe": "media_serve",
        "bridgeErrorCode": "bridge_error_code",
        "bridgeInjectTiming": "bridge_inject_timing",
    }
    for col in H5_SHELL_BRIDGE_COLUMNS:
        attr = attr_map.get(col, col)
        missing = [r.name for r in h5_rows if not getattr(r, attr, "")]
        if missing:
            violations.append(f"缺少 {col}: {', '.join(missing)}")
    return violations


def audit_programming_style_batch(rows: list[CsvTaskRow]) -> list[str]:
    """0630 弱信号：中国人风格批内 ≤ 1（小批次）或 diversity cap。"""
    n = len(rows)
    counts = Counter(r.programming_style for r in rows if r.programming_style)
    limit = _cap(n, len(counts) or 1)
    chinese = counts.get("中国人", 0)
    if chinese > max(1, limit):
        return [f"编程风格「中国人」{chinese} 次 > 批内上限 {max(1, limit)}"]
    return []


def audit_pm_cooldown(
    rows: list[CsvTaskRow],
    registry_path: Path,
    *,
    cooldown_days: int = 60,
) -> list[str]:
    """Deprecated: legacy registry cooldown — no longer used in audit."""
    _ = (rows, registry_path, cooldown_days)
    return []


def audit_designer_cooldown(
    rows: list[CsvTaskRow],
    registry_path: Path,
    *,
    cooldown_days: int = 60,
) -> list[str]:
    _ = (rows, registry_path, cooldown_days)
    return []


def audit_pm_batch_uniqueness(rows: list[CsvTaskRow]) -> list[str]:
    """Deprecated alias — batch per-dim uniqueness removed."""
    _ = rows
    return []


def audit_designer_batch_uniqueness(rows: list[CsvTaskRow]) -> list[str]:
    _ = rows
    return []


def audit_task_registry_similarity(
    rows: list[CsvTaskRow],
    registry_path: Path,
) -> list[str]:
    """Prep-phase hard check: task.csv rows vs historical contentpack registry."""
    ensure_contentpack_registry(registry_path)
    issues: list[str] = []
    issues.extend(audit_registry_duplicate_names(rows, registry_path))
    existing = load_registry_packages(registry_path)

    for row in rows:
        probe = registry_probe_from_task_row(row)
        ok, report = check_package_dict_similarity(
            probe,
            existing,
            skip_names=frozenset({row.name}),
        )
        if not ok:
            detail = next(
                (ln.strip() for ln in report.splitlines() if ln.strip().startswith("-")),
                report.splitlines()[0] if report else "registry similarity",
            )
            issues.append(
                f"「{row.name}」与历史 registry 相似（准备阶段应换主题/维度）: {detail}"
            )
    return issues


def audit_feishu_task_csv(
    csv_path: Path,
    *,
    feishu_config: Path | None = None,
) -> list[str]:
    from batch.task_feishu_sync import audit_feishu_alignment, load_feishu_prep_sources

    rows = load_csv_tasks(csv_path)
    sources = load_feishu_prep_sources(feishu_config)
    return audit_feishu_alignment(rows, sources)


def audit_task_csv(
    csv_path: Path,
    registry_path: Path,
    *,
    check_feishu: bool = True,
    feishu_config: Path | None = None,
) -> tuple[bool, list[str], list[str]]:
    rows = load_csv_tasks(csv_path)
    issues: list[str] = []
    soft: list[str] = []
    issues.extend(audit_task_registry_similarity(rows, registry_path))
    if check_feishu:
        try:
            issues.extend(audit_feishu_task_csv(csv_path, feishu_config=feishu_config))
        except (OSError, ValueError, RuntimeError) as exc:
            issues.append(f"飞书在线校验失败: {exc}")
    issues.extend(audit_dimension_diversity(rows))
    issues.extend(audit_subtitle_a_face_diversity([r.full_name for r in rows]))
    issues.extend(audit_h5_shell_bridge_filled(rows))
    issues.extend(audit_h5_kit_filled(rows))
    issues.extend(audit_programming_style_batch(rows))
    return (len(issues) == 0, issues, soft)
