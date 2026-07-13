"""Build CSV-driven prompt blocks for batch Agent phases."""

from __future__ import annotations

from batch.csv_architecture import (
    build_architecture_prompt_block,
    build_programming_style_prompt_block,
)
from batch.csv_naming import build_naming_rule_prompt_block
from pathlib import Path

from batch.csv_tasks import CsvTaskRow
from batch.iap_catalog import (
    TOTAL_PRODUCT_COUNT,
    iap_source_truth_block,
    parse_increment_style,
)


def csv_iap_block(
    row: CsvTaskRow | None,
    workspace: Path | None = None,
) -> str:
    """IAP context: CSV 首个商品Code + workspace catalog (single source of truth)."""
    if row is None:
        return iap_source_truth_block(workspace) if workspace else ""
    first_code = (row.first_product_code or "").strip()
    base_block = iap_source_truth_block(workspace)
    if not first_code:
        return base_block
    try:
        style, base = parse_increment_style(first_code)
        style_note = f"{style} (base `{base}`)"
    except ValueError as exc:
        style_note = f"INVALID — fix CSV: {exc}"
    header = (
        "[CSV IAP Context — REQUIRED]\n"
        f"- 首个商品Code(first_product_code): `{first_code}`\n"
        f"- Increment style: {style_note}\n"
        f"- All {TOTAL_PRODUCT_COUNT} productIds are listed in "
        "`iap-catalog.generated.md` (00–19 continuous; regular 12 then promo 8).\n"
        "- Implement EVERY productId from that file in native/IAP code — not only "
        "the first SKU.\n"
        "- FORBIDDEN: any `**/*.storekit` file and any "
        "`StoreKitConfigurationFileReference` in `*.xcscheme`. "
        "IAP must use App Store Connect / sandbox only "
        "(Flutter: in_app_purchase; OC/Swift: native StoreKit API).\n"
        "- If you find dangling pbxproj/scheme references to a deleted "
        "`.storekit`, strip the references — do NOT re-add the file.\n"
        "- FORBIDDEN in code: 311400, 324001, 32408, or any ID from old "
        "`内购项列表参考.md` price tables.\n"
    )
    if base_block:
        return f"{header}\n{base_block}"
    return header


def csv_full_name_block(row: CsvTaskRow | None) -> str:
    """CSV 全称 for product doc filename and format."""
    if row is None:
        return ""
    full_name = (row.full_name or "").strip()
    if not full_name:
        return ""
    return (
        "[CSV Product Doc — REQUIRED]\n"
        f"- 全称(full_name) from CSV: {full_name}\n"
        f"- Product documentation file MUST be named exactly `{full_name}.md` "
        "(not a creative variant).\n"
        "- Format: read 《H5壳产品文档格式.md》 — sections: 产品概述, App Store Listing, "
        "业务流程总结, 审核/演示路线 (Mockoo 样例).\n"
        f"- H1 MUST be: `# {full_name}`\n"
    )


def csv_architecture_block(row: CsvTaskRow | None) -> str:
    if row is None:
        return ""
    return build_architecture_prompt_block(row)


def csv_programming_style_block(
    row: CsvTaskRow | None,
    *,
    prefix: str = "",
) -> str:
    if row is None:
        return ""
    return build_programming_style_prompt_block(row, prefix=prefix)


def csv_naming_rule_block(row: CsvTaskRow | None) -> str:
    if row is None:
        return ""
    return build_naming_rule_prompt_block(row)


def dimension_boundary_block() -> str:
    """Tie-break order between the four dimensions, restated for the Agent."""
    return (
        "\n[Four Dimensions — Tie-break order]\n"
        "- Naming (命名规则): owns identifier surface for `lib/` **and** `assets/`\n"
        "  (folders, files, classes, methods, fields, params, locals, enum values,\n"
        "  raster paths in 本包资源布局.json).\n"
        "- Architecture (架构模式): owns role folders and their responsibilities;\n"
        "  it does NOT decide names — naming rule wraps every folder/class name.\n"
        "- State management (状态管理): owns top-level + cross-screen refresh;\n"
        "  must not invent new role folders and must not invent identifier styles.\n"
        "- Programming style (编程人设): owns HOW code is written (dims 1–5)\n"
        "  plus lib tree topology + asset roots (dims 6–7) — never overrides\n"
        "  names or architecture role semantics.\n"
        "- Conflict order: naming > architecture > state mgmt > programming style.\n"
    )

