"""Shared helpers for lark-cli Bitable record-list responses."""

from __future__ import annotations

from typing import Any

from batch.feishu_client import run_lark_record_list


def normalize_bitable_cell(value: Any) -> str:
    """Coerce a Bitable cell to plain text (lark-cli JSON row values)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value).strip()
    if isinstance(value, list):
        if not value:
            return ""
        return normalize_bitable_cell(value[0])
    if isinstance(value, dict):
        for key in ("text", "name", "link", "url"):
            raw = value.get(key)
            if raw:
                return str(raw).strip()
        return ""
    return str(value).strip()


def _record_list_payload(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("ok") is False:
        err = result.get("error") or {}
        msg = err.get("message") or err.get("type") or "record-list failed"
        raise RuntimeError(str(msg))
    data = result.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("record-list 响应缺少 data")
    return data


def fetch_bitable_records(
    *,
    base_token: str,
    table_id: str,
    view_id: str = "",
    page_size: int = 200,
) -> tuple[list[str], list[list[Any]]]:
    """Fetch all rows from a Bitable table. Returns (field_names, row_matrix)."""
    if page_size < 1 or page_size > 200:
        raise ValueError("page_size must be 1..200")

    field_names: list[str] = []
    rows: list[list[Any]] = []
    offset = 0

    while True:
        args = [
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--offset",
            str(offset),
            "--limit",
            str(page_size),
            "--format",
            "json",
        ]
        if view_id:
            args.extend(["--view-id", view_id])

        payload = _record_list_payload(run_lark_record_list(args, timeout=120))
        batch_fields = payload.get("fields") or []
        batch_rows = payload.get("data") or []
        if not isinstance(batch_fields, list) or not isinstance(batch_rows, list):
            raise RuntimeError("record-list 响应 fields/data 格式无效")

        if not field_names:
            field_names = [str(f) for f in batch_fields]
        elif [str(f) for f in batch_fields] != field_names:
            raise RuntimeError("record-list 分页 fields 不一致")

        rows.extend(batch_rows)
        if not payload.get("has_more"):
            break
        offset += len(batch_rows)
        if not batch_rows:
            break

    return field_names, rows


def rows_to_dicts(field_names: list[str], rows: list[list[Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        record: dict[str, str] = {}
        for idx, name in enumerate(field_names):
            if idx >= len(row):
                record[name] = ""
            else:
                record[name] = normalize_bitable_cell(row[idx])
        out.append(record)
    return out
