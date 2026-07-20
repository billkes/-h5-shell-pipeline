"""IAP catalog: iap-products.json + CSV 首个商品Code → workspace artifacts."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Literal

REGULAR_COUNT = 11
PROMO_COUNT = 7
TOTAL_PRODUCT_COUNT = REGULAR_COUNT + PROMO_COUNT

LEGACY_FORBIDDEN_IDS = frozenset(
    {
        "311400",
        "324000",
        "324001",
        "324002",
        "324003",
        "324004",
        "324005",
        "324006",
        "324007",
        "324013",
        "32408",
        "32409",
        "32410",
        "32411",
        "32412",
    }
)
LEGACY_ID_PATTERN = re.compile(r"324\d{2,3}")

IncrementStyle = Literal["prefix", "suffix"]

_CATALOG_MD_NAME = "iap-catalog.generated.md"
_JSON_NAME = "iap-products.json"


def default_products_json_path(project_dir: Path) -> Path:
    return project_dir / "data" / "static" / _JSON_NAME


def parse_increment_style(first_code: str) -> tuple[IncrementStyle, str]:
    """Parse CSV 首个商品Code into increment style and stable base name."""
    code = first_code.strip()
    if not code:
        raise ValueError("首个商品Code 为空")
    if code in LEGACY_FORBIDDEN_IDS or LEGACY_ID_PATTERN.fullmatch(code):
        raise ValueError(
            f"首个商品Code {code!r} 为旧版示例编号，请使用 Lattice00 / 00Lattice 等形式"
        )
    if re.match(r"^\d{2}[A-Za-z]", code):
        return "prefix", code[2:]
    match = re.match(r"^(.+?)(\d{2})$", code)
    if match and not code.isdigit():
        return "suffix", match.group(1)
    raise ValueError(
        f"首个商品Code {code!r} 无法解析自增规则；"
        "须为后缀式 Lattice00 或前缀式 00Lattice"
    )


def product_id_at_index(
    first_code: str,
    index: int,
    *,
    style: IncrementStyle | None = None,
    base: str | None = None,
) -> str:
    """Map catalog row index 0..19 to productId (00 起连续两位自增)."""
    if index < 0 or index >= TOTAL_PRODUCT_COUNT:
        raise IndexError(f"index must be 0..{TOTAL_PRODUCT_COUNT - 1}")
    if style is None or base is None:
        style, base = parse_increment_style(first_code)
    num = f"{index:02d}"
    if style == "prefix":
        return f"{num}{base}"
    return f"{base}{num}"


def all_product_ids(first_code: str) -> list[str]:
    style, base = parse_increment_style(first_code)
    return [
        product_id_at_index(first_code, i, style=style, base=base)
        for i in range(TOTAL_PRODUCT_COUNT)
    ]


def load_iap_products(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    regular = data.get("generalReserveSets", {}).get("products", [])
    promo = data.get("advancedStockUnits", {}).get("products", [])
    if len(regular) != REGULAR_COUNT:
        raise ValueError(f"generalReserveSets 须 {REGULAR_COUNT} 档，当前 {len(regular)}")
    if len(promo) != PROMO_COUNT:
        raise ValueError(f"advancedStockUnits 须 {PROMO_COUNT} 档，当前 {len(promo)}")
    return data


def build_catalog_rows(
    products_json: Path,
    first_code: str,
) -> list[dict[str, Any]]:
    data = load_iap_products(products_json)
    style, base = parse_increment_style(first_code)
    rows: list[dict[str, Any]] = []
    idx = 0
    for item in data["generalReserveSets"]["products"]:
        rows.append(
            {
                "productId": product_id_at_index(
                    first_code, idx, style=style, base=base
                ),
                "section": "regular",
                "sectionLabel": data["generalReserveSets"].get("label", "非促销专区"),
                "coins": item["coins"],
                "price": item["price"],
                "originalPrice": item.get("originalPrice"),
                "tags": item.get("tags") or [],
                "displayName": item.get("name", ""),
            }
        )
        idx += 1
    for item in data["advancedStockUnits"]["products"]:
        rows.append(
            {
                "productId": product_id_at_index(
                    first_code, idx, style=style, base=base
                ),
                "section": "promotional",
                "sectionLabel": data["advancedStockUnits"].get(
                    "label", "限时促销专区"
                ),
                "coins": item["coins"],
                "price": item["promoPrice"],
                "originalPrice": item["originalPrice"],
                "tags": item.get("tags") or [],
                "displayName": item.get("name", ""),
            }
        )
        idx += 1
    return rows


def render_catalog_markdown(
    first_code: str,
    rows: list[dict[str, Any]],
    *,
    increment_style: IncrementStyle,
    base: str,
) -> str:
    lines = [
        "# IAP Catalog (auto-generated — do not edit by hand)",
        "",
        "本文件由 batch 根据 `iap-products.json` + CSV 首个商品Code 生成，"
        "为**本包唯一商品数据源**。实现内购页、功能文档 IAP 章节、"
        "App Store Connect 商品 ID 均须与此表一致。",
        "",
        f"- 首个商品Code（CSV）: `{first_code}`",
        f"- 自增方式: **{increment_style}**（base `{base}`，共 "
        f"{TOTAL_PRODUCT_COUNT} 档，编号 00–{TOTAL_PRODUCT_COUNT - 1:02d} 连续）",
        "- 版式与交互: `ios-iap-page-schemes.md`（双专区、禁 App 侧超时等）",
        "- `内购项列表参考.md` 仅说明消耗型合规，**不得**抄其中旧价/324xxx",
        "",
        "## 非促销专区",
        "",
        "| productId | coins | price (USD) | tags |",
        "|-----------|-------|-------------|------|",
    ]
    for row in rows:
        if row["section"] != "regular":
            continue
        tags = ", ".join(row["tags"]) if row["tags"] else "—"
        lines.append(
            f"| {row['productId']} | {row['coins']} | {row['price']} | {tags} |"
        )
    lines.extend(
        [
            "",
            "## 限时促销专区",
            "",
            "| productId | coins | promo (USD) | original (USD) |",
            "|-----------|-------|---------------|----------------|",
        ]
    )
    for row in rows:
        if row["section"] != "promotional":
            continue
        lines.append(
            f"| {row['productId']} | {row['coins']} | {row['price']} | "
            f"{row['originalPrice']} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_catalog_artifacts(
    workspace: Path,
    *,
    project_dir: Path,
    first_code: str,
) -> Path:
    src_json = default_products_json_path(project_dir)
    if not src_json.is_file():
        raise FileNotFoundError(f"缺少 IAP 真源: {src_json}")
    shutil.copy2(src_json, workspace / _JSON_NAME)
    style, base = parse_increment_style(first_code)
    rows = build_catalog_rows(src_json, first_code)
    md = render_catalog_markdown(first_code, rows, increment_style=style, base=base)
    dest_md = workspace / _CATALOG_MD_NAME
    dest_md.write_text(md, encoding="utf-8")
    return dest_md


def copy_iap_rules_reference(docs_dir: Path, workspace: Path) -> None:
    """Copy consumable-only rules doc (no legacy price tables)."""
    src = docs_dir / "内购项列表参考.md"
    if src.is_file():
        shutil.copy2(src, workspace / "内购项列表参考.md")


def setup_iap_workspace(
    *,
    project_dir: Path,
    docs_dir: Path,
    workspace: Path,
    first_product_code: str,
) -> bool:
    """Copy JSON + rules doc; generate catalog when first_product_code is set."""
    copy_iap_rules_reference(docs_dir, workspace)
    src_json = default_products_json_path(project_dir)
    if src_json.is_file():
        shutil.copy2(src_json, workspace / _JSON_NAME)
    code = (first_product_code or "").strip()
    if not code:
        print("  >>> 警告: CSV 无首个商品Code，未生成 iap-catalog.generated.md")
        return False
    try:
        write_catalog_artifacts(
            workspace,
            project_dir=project_dir,
            first_code=code,
        )
    except (ValueError, FileNotFoundError) as exc:
        from batch.batch_log import log_detail

        log_detail(f"警告: IAP catalog 生成失败: {exc}")
        return False
    from batch.batch_log import log_detail

    log_detail(f"IAP catalog 已生成 ({TOTAL_PRODUCT_COUNT} 档 → {_CATALOG_MD_NAME})")
    return True


def iap_source_truth_block(workspace: Path | None = None) -> str:
    """Prompt block: single source of truth for IAP product data."""
    lines = [
        "[IAP Catalog — SINGLE SOURCE OF TRUTH]",
        f"- Product count: {REGULAR_COUNT} regular + {PROMO_COUNT} promotional = "
        f"{TOTAL_PRODUCT_COUNT} consumable SKUs.",
        f"- Prices, coins, tags: workspace `{_JSON_NAME}` (same as repo "
        "`data/static/iap-products.json`).",
        f"- Product IDs: workspace `{_CATALOG_MD_NAME}` — generated from CSV "
        f"首个商品Code with 00–{TOTAL_PRODUCT_COUNT - 1:02d} continuous increment "
        "(regular first, then promo).",
        "- Layout / interaction: workspace `ios-iap-page-schemes.md` "
        "(compliance + dual-section layout rules).",
        "- DO NOT use legacy IDs (311400, 324001, 32408, …) or prices from old docs.",
        "- FORBIDDEN: `**/*.storekit` and `StoreKitConfigurationFileReference` in "
        "any `*.xcscheme` — IAP uses App Store Connect / sandbox only.",
        "- `内购项列表参考.md` is consumable compliance only, not a product list.",
        "- In 功能文档.md include an **IAP Catalog** section mirroring "
        f"`{_CATALOG_MD_NAME}` tables (all productIds, coins, prices, tags).",
    ]
    if workspace is not None:
        catalog = workspace / _CATALOG_MD_NAME
        if catalog.is_file():
            lines.append("")
            lines.append(catalog.read_text(encoding="utf-8").strip())
    return "\n".join(lines)


def scan_lib_dart_text(flutter_dir: Path) -> str:
    lib = flutter_dir / "lib"
    if not lib.is_dir():
        return ""
    chunks: list[str] = []
    for path in lib.rglob("*.dart"):
        if {"build", ".dart_tool"} & set(path.parts):
            continue
        chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def verify_iap_catalog(
    flutter_dir: Path,
    workspace: Path,
    first_product_code: str,
) -> list[str]:
    """Static IAP checks after Phase 3."""
    issues: list[str] = []
    code = (first_product_code or "").strip()
    if not code:
        return issues

    catalog_md = workspace / _CATALOG_MD_NAME
    if not catalog_md.is_file():
        issues.append(f"工作区缺少 {_CATALOG_MD_NAME}（batch 应已生成）")
        return issues

    try:
        expected_ids = all_product_ids(code)
    except ValueError as exc:
        issues.append(str(exc))
        return issues

    lib_text = scan_lib_dart_text(flutter_dir)
    if not lib_text:
        issues.append("lib/ 缺失，无法校验 IAP catalog")
        return issues

    for legacy in LEGACY_FORBIDDEN_IDS:
        if legacy in lib_text:
            issues.append(f"lib 仍含旧版 IAP ID {legacy!r}，须改用 {_CATALOG_MD_NAME}")

    for match in LEGACY_ID_PATTERN.finditer(lib_text):
        token = match.group(0)
        if token not in LEGACY_FORBIDDEN_IDS:
            issues.append(f"lib 含疑似旧版编号 {token!r}")

    missing: list[str] = []
    for pid in expected_ids:
        if (
            f"'{pid}'" not in lib_text
            and f'"{pid}"' not in lib_text
            and f"productId: {pid}" not in lib_text
        ):
            missing.append(pid)
    if missing:
        preview = ", ".join(missing[:5])
        extra = f" 等共 {len(missing)} 个" if len(missing) > 5 else ""
        issues.append(
            f"IAP catalog 中有 {len(expected_ids)} 个 productId，"
            f"lib 未找到: {preview}{extra}"
        )

    if f"'{code}'" not in lib_text and f'"{code}"' not in lib_text:
        issues.append(f"CSV 首个商品Code {code!r} 未在 lib/**/*.dart 中找到")

    return issues


def _cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Setup IAP files in app workspace")
    parser.add_argument("workspace", type=Path)
    parser.add_argument("first_product_code", nargs="?", default="")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=None,
        help="defaults to project-dir / docs",
    )
    args = parser.parse_args(argv)
    docs = args.docs_dir or (args.project_dir / "docs")
    ok = setup_iap_workspace(
        project_dir=args.project_dir,
        docs_dir=docs,
        workspace=args.workspace.resolve(),
        first_product_code=args.first_product_code,
    )
    return 0 if ok or not args.first_product_code else 1


if __name__ == "__main__":
    sys.exit(_cli_main())
