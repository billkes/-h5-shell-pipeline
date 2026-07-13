"""Batch firewall: task.csv validation before production (4.3 / anti-correlation)."""

from __future__ import annotations

from pathlib import Path

from batch.config import BatchConfig
from batch.csv_tasks import CsvTaskRow, load_csv_tasks, load_task_csv_meta, output_workspace_exists
from batch.task_audit import (
    audit_dimension_diversity,
    audit_programming_style_batch,
    audit_task_registry_similarity,
)
from batch.name_rules import validate_product_code
from batch.pack_type import is_h5_shell
from batch.task_audit import audit_h5_shell_bridge_filled
from batch.task_schema import (
    COL_AUDIENCE,
    COL_CORE_SCENE,
    COL_FULL_NAME,
    COL_LOCAL_FEATURE,
    COL_THEME_CN,
    H5_SHELL_BRIDGE_COLUMNS,
)


def _duplicate_values(rows: list[CsvTaskRow], attr: str, label: str) -> list[str]:
    seen: dict[str, str] = {}
    issues: list[str] = []
    for row in rows:
        val = str(getattr(row, attr, "") or "").strip()
        if not val:
            continue
        owner = seen.get(val)
        if owner and owner != row.name:
            issues.append(f"批次内{label}重复: {val!r}（{owner} vs {row.name}）")
        else:
            seen.setdefault(val, row.name)
    return issues


def validate_batch_firewall(
    cfg: BatchConfig,
    *,
    csv_path: Path | None = None,
    queue_path: Path | None = None,
    default_type: str = "h5_swift_shell",
    skip_feishu: bool = True,
) -> bool:
    """Validate task.csv before batch run — verification only, no assignment."""
    _ = (queue_path, default_type)
    csv_path = (csv_path or cfg.task_csv).resolve()
    print("──── 批次防火墙（4.3 / 防关联）────")

    issues: list[str] = []
    try:
        rows = load_csv_tasks(csv_path, strict_extended=True, project_dir=cfg.project_dir)
        meta = load_task_csv_meta(csv_path)
        batch_id = cfg.batch_id or meta.batch_id
        if not batch_id:
            issues.append("task.csv 缺少 # batchId 注释")
    except (OSError, ValueError) as exc:
        print(f"错误: 无法读取任务台账 {csv_path}: {exc}")
        print("")
        return False

    issues.extend(_duplicate_values(rows, "first_product_code", "首个商品Code"))
    output_dir = cfg.project_dir / "output"
    for row in rows:
        code = (row.first_product_code or "").strip()
        if not code:
            continue
        if output_workspace_exists(output_dir, row):
            continue
        for issue in validate_product_code(code):
            issues.append(f"「{row.name}」{issue}")
    issues.extend(_duplicate_values(rows, "full_name", "全称"))
    issues.extend(_duplicate_values(rows, "name", "应用主名称"))
    issues.extend(_duplicate_values(rows, "theme_cn", COL_THEME_CN))
    issues.extend(_duplicate_values(rows, "core_scene", COL_CORE_SCENE))

    if not skip_feishu:
        try:
            from batch.task_feishu_sync import audit_feishu_alignment, load_feishu_prep_sources

            sources = load_feishu_prep_sources()
            issues.extend(audit_feishu_alignment(rows, sources))
        except (OSError, ValueError, RuntimeError) as exc:
            issues.append(
                f"飞书在线校验失败: {exc}（先运行 `python3 -m batch task sync-feishu`）"
            )

    issues.extend(audit_dimension_diversity(rows))
    ensure_contentpack_registry(cfg.contentpack_registry)
    issues.extend(audit_task_registry_similarity(rows, cfg.contentpack_registry))
    issues.extend(audit_h5_shell_bridge_filled(rows))
    # Kit 八维列暂未纳入 h5-shell-pipeline task.csv schema
    issues.extend(audit_programming_style_batch(rows))

    h5_names = [r.name for r in rows if is_h5_shell(r.pack_type) and r.name]
    if h5_names:
        from batch.interaction_topology import audit_batch_topology_duplicates

        issues.extend(
            audit_batch_topology_duplicates(
                cfg.project_dir,
                h5_names,
                batch_id=batch_id,
            )
        )

    from batch.theme_audit import audit_theme_rows, format_theme_audit_failure

    theme_failures: list[str] = []
    for row_index, row_name, result in audit_theme_rows(rows):
        if not result.ok:
            theme_failures.append(
                format_theme_audit_failure(
                    row_index,
                    row_name,
                    result,
                    csv_path=str(csv_path),
                )
            )
    if theme_failures:
        print("自拟主题叙事校验未通过:")
        for block in theme_failures:
            print(block)
            print("")
        print("")
        return False

    required = (
        ("state_management", "状态管理"),
        ("architecture_pattern", "架构模式"),
        ("naming_obfuscation_rule", "命名混淆规则"),
        ("first_product_code", "首个商品Code"),
        ("theme_cn", COL_THEME_CN),
        ("track", "赛道分类"),
        ("audience", COL_AUDIENCE),
        ("core_scene", COL_CORE_SCENE),
        ("local_feature", COL_LOCAL_FEATURE),
        ("pack_type", "应用类型"),
    )
    for row in rows:
        for attr, label in required:
            if not str(getattr(row, attr, "") or "").strip():
                issues.append(f"「{row.name}」缺少 CSV 字段: {label}")
        if is_h5_shell(row.pack_type):
            for col in H5_SHELL_BRIDGE_COLUMNS:
                bridge_attrs = {
                    "webviewEngine": "webview_engine",
                    "bridgeCallStyle": "bridge_call_style",
                    "bridgeCallbackStyle": "bridge_callback_style",
                    "bridgeEnvelope": "bridge_envelope",
                    "mediaServe": "media_serve",
                    "bridgeErrorCode": "bridge_error_code",
                    "bridgeInjectTiming": "bridge_inject_timing",
                }
                a = bridge_attrs.get(col, col)
                if not getattr(row, a, ""):
                    issues.append(f"「{row.name}」缺少 Bridge 字段: {col}")
    if issues:
        print("批次防火墙未通过:")
        for item in issues:
            print(f"  ! {item}")
        print("")
        return False

    print(
        f"通过 · batchId={batch_id} · {len(rows)} 个应用 · "
        "task.csv 已预分配差异化（产包阶段只验签）"
    )
    print("")
    return True
