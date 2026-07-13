"""Fetch 产 A 总库 from Feishu Bitable (online only, no local CSV cache)."""

from __future__ import annotations

from typing import Any

from batch.feishu_bitable import fetch_bitable_records, rows_to_dicts
from batch.feishu_config import get_base_token, get_prod_a_task_config
from batch.prod_a_registry import (
    COL_APP_NAME,
    COL_FIRST_CODE,
    COL_FULL_NAME,
    ProdARegistryEntry,
    build_prod_a_registry,
    format_registry_summary,
)


def _field_map(config: dict[str, Any]) -> dict[str, str]:
    """Logical key → Bitable column name."""
    fields = config.get("fields") or {}
    return {
        "app_name": str(fields.get("app_name") or COL_APP_NAME),
        "full_name": str(fields.get("full_name") or COL_FULL_NAME),
        "first_product_code": str(
            fields.get("first_product_code") or COL_FIRST_CODE
        ),
    }


def fetch_prod_a_entries(config: dict[str, Any]) -> list[ProdARegistryEntry]:
    prod = get_prod_a_task_config(config)
    base_token = get_base_token(config)
    table_id = str(prod.get("table_id") or "").strip()
    if not table_id:
        raise ValueError("feishu.yaml 缺少 prod_a_task.table_id")

    view_id = str(prod.get("view_id") or "").strip()
    field_map = _field_map(prod)
    field_names, rows = fetch_bitable_records(
        base_token=base_token,
        table_id=table_id,
        view_id=view_id,
    )
    records = rows_to_dicts(field_names, rows)

    missing = [
        col
        for col in field_map.values()
        if col and col not in field_names
    ]
    if missing:
        raise ValueError(f"Bitable 缺少列: {', '.join(missing)}")

    entries: list[ProdARegistryEntry] = []
    seen_apps: set[str] = set()
    for record in records:
        app = record.get(field_map["app_name"], "").strip()
        if not app or app in seen_apps:
            continue
        seen_apps.add(app)
        entries.append(
            ProdARegistryEntry(
                app_name=app,
                full_name=record.get(field_map["full_name"], "").strip(),
                first_product_code=record.get(
                    field_map["first_product_code"], ""
                ).strip(),
            )
        )
    return entries


def probe_prod_a_registry(config: dict[str, Any]) -> dict[str, Any]:
    """Fetch and summarize without writing any local file."""
    prod = get_prod_a_task_config(config)
    entries = fetch_prod_a_entries(config)
    if not entries:
        raise RuntimeError("产 A Bitable 无有效行（应用主名称为空）")

    table_id = str(prod.get("table_id") or "")
    registry = build_prod_a_registry(entries, source=f"feishu:{table_id}")
    return {
        "source": registry.source,
        "entries": len(entries),
        "table_id": table_id,
        "summary": format_registry_summary(registry),
    }
